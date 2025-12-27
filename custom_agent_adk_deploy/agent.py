# THis is the same code as simple_conditional but deployed using the web

import logging

from typing import AsyncGenerator , Optional
from typing_extensions import override

from google.adk.agents import LlmAgent, BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.agents.callback_context import CallbackContext
from google.adk.models import LlmRequest, LlmResponse
from google.adk.events import Event
import sys
from google.genai import types # Import necessary types


# --- Constants ---
APP_NAME = "simpleConditional"
USER_ID = "shijum"
SESSION_ID = "ses1111"
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
    # Declare the agents passed during initialization as class attributes 
    number_generator: LlmAgent
    critic: LlmAgent
    fan: LlmAgent


    # Pydantic raises an error if a field's type annotation is for a custom or third-party type, that it cannot process.
    # Enable below line to supress the error
    # model_config = {"arbitrary_types_allowed": True}

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

        # 1. Initial Number Generation
        logger.info(f"[{self.name}] Generating number...")
        async for event in self.number_generator.run_async(ctx):
            yield event

        
        logger.info(f' The generated number is = {ctx.session.state["current_number"]}')
        # Check if Number was generated before proceeding
        if "current_number" not in ctx.session.state or not ctx.session.state["current_number"] or  'roll' in ctx.session.state["current_number"]:
             logger.info(f"[{self.name}] Failed to Roll the dice. Aborting workflow.")
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



def before_model_callback_roll(
    callback_context: CallbackContext, llm_request: LlmRequest
) -> Optional[LlmResponse]:
    # Gatekeeper logic 
    # Iterate in the reverse order and pick the last user input
    if llm_request.contents:
        # Process the last user message for sanitization
        last_user_content_index = -1
        for i in range(len(llm_request.contents) - 1, -1, -1):
            if llm_request.contents[i].role == "user":
                last_user_content_index = i
                break

        if (
            last_user_content_index != -1
            and llm_request.contents[last_user_content_index].parts
        ):
            user_input = llm_request.contents[last_user_content_index].parts[0].text

        #  Check The Decision
        if user_input == "roll":
            logger.info("Validation SUCCESS: Command 'roll' confirmed.")
        else:
            logger.error(f"Validation FAILED: Expected 'roll', received '{user_input}'")
            return LlmResponse(
                content=types.Content(
                    role="model",
                    parts=[types.Part(text="To generate a number enter : roll")],
                )
            )            
    return None


# --- Define the individual LLM agents ---
number_generator = LlmAgent(
    name="NumberGenerator",
    model=GEMINI_2_FLASH,
    instruction="""You are a dice. Return a number between 1 & 6 """,
    input_schema=None,
    before_model_callback=before_model_callback_roll,
    output_key="current_number",  # Key for storing the number in session state
)

critic = LlmAgent(
    name="Critic",
    model=GEMINI_2_FLASH,
    instruction="""You are a  critic. return a one word negative response , the severity is determied by the input number {{current_number}}""",
    input_schema=None,
    output_key="message",  # Key for storing the response in session state
)

fan = LlmAgent(
    name="Fan",
    model=GEMINI_2_FLASH,
    instruction="""You are a  fan. return a one word positive response , the severity is determied by the input number {{current_number}}""",
    input_schema=None,
    output_key="message",  # Key for storing the response in session state
)


# --- Create the custom agent instance ---
simple_flow_agent = SimpleAgent(
    name="SimpleAgent",
    number_generator=number_generator,
    critic=critic,
    fan=fan,

)

root_agent = simple_flow_agent