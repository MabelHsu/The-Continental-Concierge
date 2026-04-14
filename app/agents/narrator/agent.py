"""
Narrative Director — The only agent that produces user-facing prose.

Takes structured outputs from all other agents and weaves them into
cinematic, consistent, atmospheric narrative for the player.
"""

from google.adk.agents import Agent
from google.adk.tools import FunctionTool

from app.shared.config import config
from app.tools.lore_tools import search_lore
from app.tools.world_state_tools import get_world_state

NARRATOR_INSTRUCTION = open("app/agents/narrator/prompt.md", "r").read()

narrator_agent = Agent(
    name="narrator",
    model=config.model_name,
    instruction=NARRATOR_INSTRUCTION,
    # No tools. The narrator receives all data it needs from the orchestrator
    # via the transfer_to_agent message. Giving it tools (especially get_world_state)
    # caused it to shortcut — calling get_world_state itself and fabricating a
    # "no missions available" response instead of waiting for the orchestrator to
    # provide real mission data from get_available_missions().
    tools=[],
    generate_content_config={
        "temperature": 0.85,
        "max_output_tokens": 4096,
    },
)
