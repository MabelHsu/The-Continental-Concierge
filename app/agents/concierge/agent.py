"""
Concierge Orchestrator — Entry point and task router.

This is the root agent registered with Vertex AI Agent Engine.
It decomposes user input into tasks, calls specialists, runs consistency
checks, and hands everything to the Narrative Director for final output.
"""

from google.adk.agents import Agent, SequentialAgent, ParallelAgent
from google.adk.tools import FunctionTool
from google.adk.models import Gemini

from app.shared.config import config
from app.shared.types import Task, TaskType, AgentResult, WorldSnapshot
from app.agents.archivist.agent import archivist_agent
from app.agents.ledger.agent import ledger_agent
from app.agents.timeline.agent import timeline_agent
from app.agents.narrator.agent import narrator_agent
from app.tools.world_state_tools import get_world_state, advance_time
from app.tools.consistency_tools import check_consistency


# ── Tool definitions the orchestrator can call directly ──────────────────

get_world_state_tool = FunctionTool(func=get_world_state)
advance_time_tool = FunctionTool(func=advance_time)
consistency_tool = FunctionTool(func=check_consistency)


# ── Specialist sub-agents ────────────────────────────────────────────────

# Each specialist is an Agent with its own prompt and tools.
# The orchestrator calls them via ADK's agent-to-agent delegation.


# ── The Orchestrator ─────────────────────────────────────────────────────

ORCHESTRATOR_INSTRUCTION = open(
    "app/agents/concierge/prompt.md", "r"
).read()

concierge_orchestrator = Agent(
    name="concierge_orchestrator",
    model=config.model_name,
    instruction=ORCHESTRATOR_INSTRUCTION,
    tools=[
        get_world_state_tool,
        advance_time_tool,
        consistency_tool,
    ],
    sub_agents=[
        archivist_agent,
        ledger_agent,
        timeline_agent,
        narrator_agent,
    ],
    # ADK config
    output_key="final_response",
    generate_content_config={
        "temperature": 0.7,
        "max_output_tokens": 4096,
    },
)


# ── Agent Engine entry point ─────────────────────────────────────────────

root_agent = concierge_orchestrator
