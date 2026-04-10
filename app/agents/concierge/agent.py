"""
Concierge Orchestrator — Entry point and task router.

This is the root agent registered with Vertex AI Agent Engine.

Routing sequence on each turn:
  1. Check player state (onboarding complete?)
  2. If not complete → delegate to Onboarding Agent (Charon check-in)
  3. If complete → parse request, dispatch specialists in parallel where safe,
     run consistency check, hand to Narrative Director for final prose.

Player context is injected into every specialist call so the world responds
to who the player IS, not just what they're asking.
"""

from google.adk.agents import Agent
from google.adk.tools import FunctionTool

from app.shared.config import config
from app.shared.types import Task, TaskType, AgentResult, WorldSnapshot
from app.agents.archivist.agent import archivist_agent
from app.agents.ledger.agent import ledger_agent
from app.agents.timeline.agent import timeline_agent
from app.agents.narrator.agent import narrator_agent
from app.agents.onboarding.agent import onboarding_agent
from app.tools.world_state_tools import get_world_state, advance_time
from app.tools.consistency_tools import check_consistency
from app.tools.player_tools import (
    get_player,
    get_available_missions,
    accept_mission,
    complete_mission,
    update_player_reputation,
    update_player_location,
    spend_gold,
    earn_gold,
    add_inventory_item,
    get_inventory,
    update_faction_standing,
)


# ── Direct orchestrator tools ─────────────────────────────────────────────────
# These are called by the orchestrator itself, not delegated to sub-agents.

ORCHESTRATOR_DIRECT_TOOLS = [
    # World
    FunctionTool(func=get_world_state),
    FunctionTool(func=advance_time),
    FunctionTool(func=check_consistency),
    # Player state reads
    FunctionTool(func=get_player),
    FunctionTool(func=get_available_missions),
    FunctionTool(func=get_inventory),
    # Player state writes (orchestrator applies after specialist routing)
    FunctionTool(func=accept_mission),
    FunctionTool(func=complete_mission),
    FunctionTool(func=update_player_reputation),
    FunctionTool(func=update_player_location),
    FunctionTool(func=spend_gold),
    FunctionTool(func=earn_gold),
    FunctionTool(func=add_inventory_item),
    FunctionTool(func=update_faction_standing),
]


# ── Sub-agents ────────────────────────────────────────────────────────────────
# Ordered by typical call frequency. Onboarding first — it gates everything else.

SUB_AGENTS = [
    onboarding_agent,   # Check-in / character creation — gates all other routing
    archivist_agent,    # Lore, characters, rules, history
    ledger_agent,       # Debts, markers, reputation, relationships
    timeline_agent,     # Events, locations, collision detection
    narrator_agent,     # Final cinematic prose (always last)
]


# ── The Orchestrator ──────────────────────────────────────────────────────────

ORCHESTRATOR_INSTRUCTION = open(
    "app/agents/concierge/prompt.md", "r"
).read()

concierge_orchestrator = Agent(
    name="concierge_orchestrator",
    model=config.model_name,
    instruction=ORCHESTRATOR_INSTRUCTION,
    tools=ORCHESTRATOR_DIRECT_TOOLS,
    sub_agents=SUB_AGENTS,
    output_key="final_response",
    generate_content_config={
        # Balanced temperature: needs precision for routing, slight creativity
        # for synthesising multi-agent outputs into a coherent plan.
        "temperature": 0.7,
        "max_output_tokens": 4096,
    },
)


# ── Agent Engine entry point ──────────────────────────────────────────────────
# Vertex AI Agent Engine expects a `root_agent` export.

root_agent = concierge_orchestrator
