"""
Onboarding Agent — Charon conducts the player's check-in.

Handles both identity paths:
  - Mystery: player arrives as unknown; identity assembles from 5 exchanges.
  - Custom: player declares themselves; 4 structured exchanges.

The agent runs as a sub-agent of the Concierge Orchestrator. It is only
invoked when `player.onboarding_complete == False`. Once complete, it
hands off to the standard orchestration loop.

This agent IS user-facing (unlike every other specialist). The Narrator
is bypassed during onboarding — Charon's lines are the output.
"""

from google.adk.agents import Agent
from google.adk.tools import FunctionTool

from app.shared.config import config
from app.tools.lore_tools import lookup_character, search_lore
from app.tools.player_tools import (
    advance_onboarding_step,
    complete_onboarding,
    create_player_character,
    get_player,
    update_player_location,
)
from app.tools.world_state_tools import get_world_state

ONBOARDING_INSTRUCTION = open("app/agents/onboarding/prompt.md", "r").read()

onboarding_agent = Agent(
    name="onboarding",
    model=config.model_name,
    instruction=ONBOARDING_INSTRUCTION,
    tools=[
        FunctionTool(func=create_player_character),
        FunctionTool(func=advance_onboarding_step),
        FunctionTool(func=complete_onboarding),
        FunctionTool(func=get_player),
        FunctionTool(func=update_player_location),
        FunctionTool(func=lookup_character),
        FunctionTool(func=search_lore),
        FunctionTool(func=get_world_state),
    ],
    generate_content_config={
        # 0.4 reduces the `print(default_api.xxx())` malformed-call sampling
        # error while still giving Charon enough variation to feel alive.
        # If lines feel flat, try 0.5. Never go above 0.6 — the model starts
        # generating Python code wrappers at higher temperatures.
        "temperature": 0.4,
        "max_output_tokens": 1024,
    },
    # This agent IS user-facing during onboarding.
    # Its charon_line field goes directly to the player without
    # passing through the Narrative Director.
    output_key="onboarding_response",
)
