import asyncio
import logging

from typing import AsyncGenerator
from typing_extensions import override

from google.adk.agents import LlmAgent, BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.genai import types
from google.adk.runners import Runner
from google.adk.events import Event
from google.adk.sessions import InMemorySessionService
import json

# --- Constants ---
APP_NAME = "simpleConditional"
USER_ID = "shijum"
SESSION_ID = "123344"
GEMINI_2_FLASH = "gemini-2.0-flash"


# --- Configure Logging ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# --- Custom Orchestrator Agent ---
class SimpleAgent(BaseAgent):
    """
    Custom agent for a Simple conditional test.
    """

    # --- Field Declarations for Pydantic ---
    # Declare the agents passed during initialization as class attributes with type hints
    number_generator: LlmAgent
    critic: LlmAgent
    fan: LlmAgent


    # model_config allows setting Pydantic configurations if needed, e.g., arbitrary_types_allowed
    model_config = {"arbitrary_types_allowed": True}

    def __init__(
        self,
        name: str,
        number_generator: LlmAgent,
        critic: LlmAgent,
        fan: LlmAgent 
    ):
        """
        Initializes the SimpleAgent.
        """

        # # Define the sub_agents list for the framework
        # sub_agents_list = [
        #     story_generator,
        #     loop_agent,
        #     sequential_agent,
        # ]

        # Pydantic will validate and assign them based on the class annotations.
        super().__init__(
            name=name,
            number_generator=number_generator,
            critic=critic,
            fan=fan
        )

    @override
    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        """
        Implements the custom orchestration logic for the  workflow.
        """
        logger.info(f"[{self.name}] Starting  workflow.")

        # 1. Initial Story Generation
        logger.info(f"[{self.name}] Generating number...")
        async for event in self.number_generator.run_async(ctx):
            # logger.info(f"[{self.name}] Event from StoryGenerator: {event.model_dump_json(indent=2, exclude_none=True)}")
            yield event

        # Check if story was generated before proceeding
        if "current_number" not in ctx.session.state or not ctx.session.state["current_number"]:
             logger.error(f"[{self.name}] Failed to generate initial story. Aborting workflow.")
             return # Stop processing if the die was not rolled

        rolled_number = ctx.session.state.get('current_number')
        logger.info(f"[{self.name}] Number state after generator: {rolled_number}")
            

        # 2. If odd number then call critic else fan. 
        if int(rolled_number) % 2 == 0:
            async for event in self.fan.run_async(ctx):
                yield event         
        else: 
            async for event in self.critic.run_async(ctx):
                yield event    

        tone_result = ctx.session.state.get("message")   
        logger.info(f"[{self.name}] Tone result: {tone_result}")

        logger.info(f"[{self.name}] Workflow finished.")

# --- Define the individual LLM agents ---
number_generator = LlmAgent(
    name="StoryGenerator",
    model=GEMINI_2_FLASH,
    instruction="""You are a dice. Return a number between 1 & 6 """,
    input_schema=None,
    output_key="current_number",  # Key for storing output in session state
)

critic = LlmAgent(
    name="Critic",
    model=GEMINI_2_FLASH,
    instruction="""You are a  critic. Return a negative response , the severity is determied by the input number {{current_number}}""",
    input_schema=None,
    output_key="message",  # Key for storing criticism in session state
)

fan = LlmAgent(
    name="Fan",
    model=GEMINI_2_FLASH,
    instruction="""You are a  critic. return a one word positive response , the severity is determied by the input number {{current_number}}""",
    input_schema=None,
    output_key="message",  # Key for storing praise in session state
)



# --- Create the custom agent instance ---
simple_flow_agent = SimpleAgent(
    name="SimpleAgent",
    number_generator=number_generator,
    critic=critic,
    fan=fan
)

# --- Setup Runner and Session ---
async def setup_session_and_runner():
    session_service = InMemorySessionService()
    session = await session_service.create_session(app_name=APP_NAME, user_id=USER_ID, session_id=SESSION_ID)
    logger.info(f"Initial session state: {session.state}")
    runner = Runner(
        agent=simple_flow_agent, # Pass the custom orchestrator agent
        app_name=APP_NAME,
        session_service=session_service
    )
    return session_service, runner

# --- Function to Interact with the Agent ---
async def call_agent_async():

    session_service, runner = await setup_session_and_runner()

    current_session = await session_service.get_session(app_name=APP_NAME, 
                                                  user_id=USER_ID, 
                                                  session_id=SESSION_ID)
    if not current_session:
        logger.error("Session not found!")
        return


    content = types.Content(role='user', parts=[types.Part(text=f"Roll a die")])
    events = runner.run_async(user_id=USER_ID, session_id=SESSION_ID, new_message=content)
    # events = runner.run_async(user_id=USER_ID, session_id=SESSION_ID, new_message="" )

    print(events)
    final_response = ""
    async for event in events:
        pass
        # if event.is_final_response() and event.content and event.content.parts:
        #     logger.info(f"Potential final response from [{event.author}]: {event.content.parts[0].text}")
        #     final_response = event.content.parts[0].text

    # print("\n--- Agent Interaction Result ---")
    # print("Agent Final Response: ", final_response)

    final_session = await session_service.get_session(app_name=APP_NAME, 
                                                user_id=USER_ID, 
                                                session_id=SESSION_ID)
    # print("Final Session State:")
    print(f"Rolled number: {final_session.state.get('current_number') } and the message is : {final_session.state.get('message') } ")
    print("-------------------------------\n")




asyncio.run( call_agent_async())