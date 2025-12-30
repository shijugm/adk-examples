"""
BigQuery integration tools for the cookie delivery system using Google ADK first-party toolset.
This file implements BigQuery connectivity using Google's official ADK BigQuery tools.
"""

import os
import logging
from typing import Dict, List, Optional

from google.adk.tools.bigquery import BigQueryCredentialsConfig, BigQueryToolset
from google.adk.tools.bigquery.config import BigQueryToolConfig, WriteMode
from google.adk.tools.tool_context import ToolContext
import google.auth

# BigQuery Configuration
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "your-project-id")
DATASET_ID = "cookie_delivery"
ORDERS_TABLE = "orders"

# Initialize the ADK BigQuery Toolset
def get_bigquery_toolset() -> BigQueryToolset:
    """
    Create and configure the ADK BigQuery toolset.
    Uses Application Default Credentials for authentication.
    """
    try:
        # Tool configuration - allows write operations for order management
        tool_config = BigQueryToolConfig(write_mode=WriteMode.ALLOWED)
        
        # Use Application Default Credentials (most common for production)
        application_default_credentials, _ = google.auth.default()
        
        # Create credentials config for ADC
        credentials_config = BigQueryCredentialsConfig(
            credentials=application_default_credentials
        )
        
        # Initialize the BigQuery toolset
        bigquery_toolset = BigQueryToolset(
            credentials_config=credentials_config,
            bigquery_tool_config=tool_config
        )
        
        logging.info("ADK BigQuery toolset initialized successfully")
        return bigquery_toolset
        
    except Exception as e:
        logging.error(f"Failed to initialize BigQuery toolset: {e}")
        return None

# Helper functions for the cookie delivery agent using ADK tools
def get_latest_order_from_bigquery(tool_context: ToolContext) -> Dict:
    """
    Fetch the latest order with 'order_placed' status from BigQuery using ADK tools.
    This is a wrapper function that uses the ADK execute_sql tool.
    """
    logging.info("Fetching latest order from BigQuery using ADK toolset...")
    
    try:
        # The ADK toolset will be available in the agent's tools
        # This function provides the SQL query logic for the agent to use
        
        query = f"""
        SELECT *
        FROM `{PROJECT_ID}.{DATASET_ID}.{ORDERS_TABLE}`
        WHERE order_status = 'order_placed'
        ORDER BY created_at DESC
        LIMIT 5
        """
        
        # Return the query for the agent to execute using ADK execute_sql tool
        # The agent will handle the actual execution through the toolset
        return {
            "status": "query_ready",
            "query": query,
            "instruction": "Execute this query using the execute_sql tool to get the latest order",
            "expected_result": "order_data"
        }
        
    except Exception as e:
        logging.error(f"Error preparing BigQuery query: {e}")
        return {"status": "error", "message": f"Query preparation error: {str(e)}"}

def update_order_status_in_bigquery(
    tool_context: ToolContext, 
    order_number: str, 
    new_status: str
) -> Dict:
    """
    Generate SQL to update order status in BigQuery using ADK tools.
    This function now returns SQL for execution by the ADK toolset instead of executing directly.
    """
    logging.info(f"Preparing order status update for {order_number} to {new_status}...")
    
    try:
        query = f"""
        UPDATE `{PROJECT_ID}.{DATASET_ID}.{ORDERS_TABLE}`
        SET order_status = '{new_status}', 
            updated_at = CURRENT_TIMESTAMP()
        WHERE order_number = '{order_number}'
        """
        
        return {
            "status": "query_ready",
            "query": query,
            "instruction": f"Execute this query to update order {order_number} status to {new_status}",
            "order_number": order_number,
            "new_status": new_status
        }
        
    except Exception as e:
        logging.error(f"Error preparing update query: {e}")
        return {"status": "error", "message": f"Update query error: {str(e)}"}


# For environment setup, use create_bigquery_environment.py script.