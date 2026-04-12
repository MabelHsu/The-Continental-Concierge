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
    tools=[
        FunctionTool(func=get_world_state),
        FunctionTool(func=search_lore),
    ],
    generate_content_config={
        "temperature": 0.85,  # Higher creativity for narrative prose
        "max_output_tokens": 4096,
    },
)
