import os
import sys
import atexit
import logging
import google.cloud.logging
 
from dotenv import load_dotenv

from google.adk import Agent
from google.adk.agents import SequentialAgent
from google.adk.tools.tool_context import ToolContext


try:
    from .bq_utils.bq_tools import get_bigquery_toolset, get_latest_order_from_bigquery, update_order_status_in_bigquery
    # Initialize the ADK BigQuery toolset
    bigquery_toolset = get_bigquery_toolset()
    BIGQUERY_AVAILABLE = bigquery_toolset is not None
    logging.info(f"ADK BigQuery Toolset: {'Available' if BIGQUERY_AVAILABLE else 'Not available'}")
except ImportError as e:
    logging.warning(f"BigQuery ADK toolset not available: {e}")
    bigquery_toolset = None
    BIGQUERY_AVAILABLE = False


# --- Setup and Configuration ---

# Set up cloud logging
try:
    cloud_logging_client = google.cloud.logging.Client()
    cloud_logging_client.setup_logging()
    logging.info("Google Cloud Logging initialized.")
except Exception as e:
    logging.warning(f"Could not initialize Google Cloud Logging: {e}. Using basic logging.")
    logging.basicConfig(level=logging.INFO)

# This will flush the pending logs before exiting and Avoids this error - 
# CloudLoggingHandler shutting down, cannot send logs entries to Cloud Logging due to inconsistent threading behavior at shutdown. To avoid this issue, flush the logging handler manually or switch to StructuredLogHandler. You can also close the CloudLoggingHandler manually via handler.close or client.close.
# Failed to send 1 pending logs.
# Set PYTHONUNBUFFERED=1 in environment variables.
atexit.register(logging.shutdown)

# Load environment variables from a .env file
load_dotenv()
model_name = os.getenv("MODEL", "gemini-2.5-flash")

logging.info(f"Using model: {model_name}")


def get_latest_order(tool_context: ToolContext) -> dict:
    """
    Fetches the most recent order with 'order_placed' status from the database.
    """
    logging.info(" Tool: get_latest_order called.")
    
    # Use BigQuery ADK toolset if available and enabled
    if BIGQUERY_AVAILABLE:
        # With ADK toolset, we return a structured query for the agent to execute
        query_info = get_latest_order_from_bigquery(tool_context)
        if query_info.get("status") == "query_ready":
            logging.info(" BigQuery query prepared for ADK execution")
            return {
                "status": "bigquery_query_ready",
                "instruction": "Use the execute_sql tool to run this query",
                "query": query_info["query"],
                "message": "Query prepared for BigQuery ADK toolset execution"
            }
        else:
            logging.error(f" Failed to prepare BigQuery query: {query_info.get('message')}")
    
    
    logging.warning(" No new orders found with status 'order_placed'.")
    return {"status": "error", "message": "No new orders found with status 'order_placed'."}

def update_order_status(tool_context: ToolContext, order_number: str, new_status: str) -> dict:
    """
    Updates the status of a given order in the database.
    """
    logging.info(f"Tool: update_order_status called for {order_number} to set status {new_status}.")
    
    # Use BigQuery ADK toolset if available and enabled
    if BIGQUERY_AVAILABLE:
        query_info = update_order_status_in_bigquery(tool_context, order_number, new_status)
        logging.info(f" query_info = {query_info}")
        if query_info.get("status") == "query_ready":
            logging.info(" BigQuery update query prepared for ADK execution")
            return {
                "status": "bigquery_update_ready",
                "instruction": "Use the execute_sql tool to run this update query",
                "query": query_info["query"],
                "order_number": order_number,
                "new_status": new_status,
                "message": f"Update query prepared to change order {order_number} to {new_status}"
            }
        else:
            logging.error(f"Failed to prepare update query: {query_info.get('message')}")
    
    
    logging.warning(f"Order {order_number} not found.")
    return {"status": "error", "message": f"Order {order_number} not found."}

    
# --- AGENT DEFINITIONS ---

## Database Agent
# This agent's responsibility is to fetch order data from BigQuery using ADK toolset.
store_database_agent_tools = [get_latest_order , bigquery_toolset]

store_database_agent = Agent(
    name="store_database_agent",
    model=model_name,
    description="Responsible for getting and updating the BigQuery database for orders using Google's first-party ADK toolset.",
    instruction=f"""
    You are the order manager with access to the BigQuery orders database {'using Googles first-party ADK toolset' }.
    
    **BigQuery Integration Status**: {'ADK BigQuery Toolset Available' if BIGQUERY_AVAILABLE else False}
    
    Your primary job is to fetch the latest order from the database that has the status 'order_placed'.
    
    **WORKFLOW:**
    1. First, use the 'get_latest_order' tool to get query information
    2. If the response indicates "bigquery_query_ready", use the 'execute_sql' tool to run the provided query
    3. Parse the BigQuery results and save the order details to the agent state
    
    **Available Tools:**
    - get_latest_order: Prepares the query  
    {'- execute_sql: Executes SQL queries in BigQuery (ADK toolset)' if BIGQUERY_AVAILABLE else ''}
    {'- list_dataset_ids: Lists available BigQuery datasets (ADK toolset)' if BIGQUERY_AVAILABLE else ''}
    {'- get_table_info: Gets BigQuery table schema information (ADK toolset)' if BIGQUERY_AVAILABLE else ''}
    
    Make sure to handle any database connection errors gracefully and always save order details to the state.
    """,
    tools=store_database_agent_tools,
)

## Process order Agent
# This agent finalizes the order status in BigQuery.
process_order_agent_tools = [  update_order_status , bigquery_toolset]


process_order_agent = Agent(
    name="process_order_agent",
    model=model_name,
    description="Finalizes the order status in BigQuery using ADK toolset.",
    instruction=f"""
    You are the order update agent with access BigQuery ADK toolset.
    
    **Integration Status**: 
    - BigQuery: {'ADK Toolset Available' if BIGQUERY_AVAILABLE else 'Using Dummy Data'}

    Your  task is to confirm the delivery and update the order status:

    **Update Status**: Use the `update_order_status` tool to change the order status to 'scheduled'.
        {'- If the response indicates "bigquery_update_ready", use the execute_sql tool to run the provided update query' if BIGQUERY_AVAILABLE else '- This will update dummy data if BigQuery is not available'}
        - Use the order number from the state
 

    **Available Tools:**
    - update_order_status: Prepares update query 
    - execute_sql: Executes BigQuery update queries (ADK toolset)

    **Note**: All necessary information (order_details, delivery_month) will be available in the agent state from previous steps.
    """,
    tools=process_order_agent_tools,
)



# --- SEQUENTIAL WORKFLOW AGENT ---
# This agent orchestrates the sub-agents in a specific order.
delivery_workflow_agent = SequentialAgent(
    name="delivery_workflow_agent",
    description="Manages the entire cookie delivery process from order to confirmation.",
    sub_agents=[
        store_database_agent,
        process_order_agent
    ]
)

# --- ROOT AGENT ---
# The main entry point for the entire workflow.
root_agent = Agent(
    name="root_agent",
    model=model_name,
    description="The main agent that kicks off the  delivery workflow.",
    instruction="""
    You are the manager of a delivery service.
    Your goal is to process the latest incoming order.
    
    WORKFLOW:
    1. First, greet the user and ask if they would like to kick off the workflow for the week.
    2. If they say yes, start the process by transferring control to the 'delivery_workflow_agent'.
    3. Once the delivery workflow is complete, thank the user and summarize what was accomplished.
    4. DO NOT ask to restart the process unless the user explicitly requests it.
    5. If the user asks to process another order, then you can restart the workflow.
    
    Remember: Only run the workflow ONCE per user request, then wait for further instructions.
    """,
    sub_agents=[delivery_workflow_agent],
)