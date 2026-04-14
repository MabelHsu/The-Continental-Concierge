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
from google.adk.tools import AgentTool, FunctionTool

from app.agents.archivist.agent import archivist_agent
from app.agents.ledger.agent import ledger_agent
from app.agents.narrator.agent import narrator_agent
from app.agents.onboarding.agent import onboarding_agent
from app.agents.timeline.agent import timeline_agent
from app.shared.config import config
from app.tools.consistency_tools import check_consistency
from app.tools.player_tools import (
    accept_mission,
    add_inventory_item,
    complete_mission,
    earn_gold,
    get_available_missions,
    get_inventory,
    get_player,
    spend_gold,
    update_faction_standing,
    update_player_location,
    update_player_reputation,
)
from app.tools.world_state_tools import advance_time, get_world_state

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
    # ── Specialist agents wrapped as AgentTool ────────────────────────────────
    # AgentTool (not sub_agent) means the specialist runs and its response
    # is returned to the orchestrator as a tool result — not sent to the user.
    # The orchestrator then passes that data to the narrator for final prose.
    # (sub_agents use transfer_to_agent which is a terminal handoff — the
    # specialist's raw JSON would go directly to the user, bypassing the Narrator.)
    AgentTool(agent=archivist_agent),  # Lore, characters, rules, history
    AgentTool(agent=ledger_agent),  # Debts, markers, reputation
    AgentTool(agent=timeline_agent),  # Events, locations, collisions
]


# ── Sub-agents ────────────────────────────────────────────────────────────────
# Only agents that produce the FINAL user-facing response go here.
# transfer_to_agent is a terminal handoff — their output goes straight to the user.

SUB_AGENTS = [
    onboarding_agent,  # Terminal: Charon speaks directly during check-in
    narrator_agent,  # Terminal: always the last step — converts data to prose
]


# ── The Orchestrator ──────────────────────────────────────────────────────────

ORCHESTRATOR_INSTRUCTION = open("app/agents/concierge/prompt.md", "r").read()

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
