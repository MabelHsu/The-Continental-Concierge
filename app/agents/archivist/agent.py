"""
Archivist Agent — The hotel's memory.

Retrieves lore, character history, hotel rules, and past events using
AlloyDB hybrid retrieval (structured queries + vector search).
"""

from google.adk.agents import Agent
from google.adk.tools import FunctionTool

from app.shared.config import config
from app.tools.lore_tools import (
    lookup_character,
    lookup_rule,
    search_lore,
    get_character_history,
)
from app.tools.world_state_tools import get_events, get_world_state


ARCHIVIST_INSTRUCTION = open(
    "app/agents/archivist/prompt.md", "r"
).read()

archivist_agent = Agent(
    name="archivist",
    model=config.model_name,
    instruction=ARCHIVIST_INSTRUCTION,
    tools=[
        FunctionTool(func=lookup_character),
        FunctionTool(func=lookup_rule),
        FunctionTool(func=search_lore),
        FunctionTool(func=get_character_history),
        FunctionTool(func=get_events),
        FunctionTool(func=get_world_state),
    ],
    generate_content_config={
        "temperature": 0.3,  # Low creativity for factual retrieval
        "max_output_tokens": 2048,
    },
)
