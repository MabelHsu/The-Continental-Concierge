"""
Timeline Agent — Temporal and spatial consistency engine.

Tracks character locations, event chronology, and detects collisions
(scheduling conflicts, hostile co-presence, deadline breaches).
"""

from google.adk.agents import Agent
from google.adk.tools import FunctionTool

from app.shared.config import config
from app.tools.timeline_tools import (
    get_current_locations,
    move_character,
    log_event,
    get_timeline,
    detect_collisions,
    get_upcoming_deadlines,
    check_character_availability,
)


TIMELINE_INSTRUCTION = open(
    "app/agents/timeline/prompt.md", "r"
).read()

timeline_agent = Agent(
    name="timeline",
    model=config.model_name,
    instruction=TIMELINE_INSTRUCTION,
    tools=[
        FunctionTool(func=get_current_locations),
        FunctionTool(func=move_character),
        FunctionTool(func=log_event),
        FunctionTool(func=get_timeline),
        FunctionTool(func=detect_collisions),
        FunctionTool(func=get_upcoming_deadlines),
        FunctionTool(func=check_character_availability),
    ],
    generate_content_config={
        "temperature": 0.2,
        "max_output_tokens": 2048,
    },
)
