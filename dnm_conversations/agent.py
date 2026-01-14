from google.adk import Agent
from google.adk.apps import App
from toolbox_core import ToolboxSyncClient

client = ToolboxSyncClient("http://127.0.0.1:5001")

root_agent = Agent(
    name='root_agent',
    model='gemini-2.5-flash',
    instruction="""
    You are a logistics assistant. 
    1. For general shipment questions, help the user normally.
    2. For status-specific searches, you MUST map natural language to codes:
       - 'delivered' -> 'D'
       - 'moving' or 'in transit' -> 'T'
       - 'at facility' or 'warehouse' -> 'F'
    3. Use 'check_network_congestion' to find facilities that are overcrowded or acting as bottlenecks. 
       - If a user asks 'Is the network busy?', run this tool with a default threshold.
        - Suggest checking the articles at the facility using  'get_articles_dwelling_at_facility'. 
    4. Use 'get_longest_open_journeys' to find delayed items.
       - Note: The 'duration' returned is in  Minutes. 
       - Always report the specific duration to the user so they understand the severity of the delay.
    5. If the user asks for something outside logistics (like weather or jokes), 
       kindly refocus them on the logistics operations.
    """,    
    tools=client.load_toolset(),
)

