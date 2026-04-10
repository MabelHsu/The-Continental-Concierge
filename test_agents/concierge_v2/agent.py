"""
Continental Concierge — Phase 1d: Multi-Agent Orchestrator

ADK PATTERN USED HERE — Important to understand:

  WRONG pattern (what we had before):
    sub_agents = [archivist, ledger, timeline, narrator]
    → When orchestrator "transfers" to archivist, archivist owns the response.
    → Orchestrator never gets the data back. Can't chain to narrator.
    → Result: user sees raw JSON from archivist.

  CORRECT pattern (what we use now):
    tools      = [AgentTool(archivist), AgentTool(ledger), AgentTool(timeline)]
    sub_agents = [narrator]
    → AgentTool wraps an agent as a callable tool.
    → Orchestrator calls archivist_tool(), gets data BACK as a tool result.
    → Orchestrator then transfers to narrator with that data.
    → Result: user sees prose from narrator. ✓

  Rule of thumb:
    - Data agents that feed INTO other agents → AgentTool
    - Agents that produce the FINAL response → sub_agents

Run with:
  adk web test_agents/
  → open http://localhost:8000
  → select "concierge_v2" from the agent dropdown
"""

from google.adk.agents import Agent
from google.adk.tools.agent_tool import AgentTool

from .archivist import archivist_agent
from .narrator import narrator_agent
from .ledger import ledger_agent
from .timeline import timeline_agent


# ── Wrap data agents as tools ─────────────────────────────────────────────────
# AgentTool means the orchestrator calls these like function tools and gets
# their output back — it does NOT hand over control to them permanently.

archivist_tool = AgentTool(agent=archivist_agent)
ledger_tool    = AgentTool(agent=ledger_agent)
timeline_tool  = AgentTool(agent=timeline_agent)


# ── Root Orchestrator ─────────────────────────────────────────────────────────

root_agent = Agent(
    name="concierge_orchestrator",
    model="gemini-2.5-flash",
    instruction="""You are the Concierge Orchestrator for The Continental Hotel, New York City.

## Your Tools

- `archivist` — facts about characters, rules, lore, history
- `ledger`    — debts, markers, reputation, relationships
- `timeline`  — current world state, locations, collisions, deadlines
- `narrator`  — the ONLY voice to the player. Transfer to this LAST, always.

## Decision Rules — Pick Your Path Before Acting

Read the query once. Classify it as ONE of these paths. Then execute the
entire path without stopping.

### Path A — Single domain query
Query touches only one domain → call that one tool → transfer to narrator.

Examples:
- "Who is Charon?" → archivist → narrator
- "What does John owe?" → ledger → narrator
- "Where is Winston?" → timeline → narrator
- "What's the rule about sanctuary?" → archivist → narrator

### Path B — Multi-domain query
Query explicitly asks about multiple things ("everything about X", "who he is
AND what he owes AND where he is") → call ALL relevant tools first, in order,
then transfer to narrator ONCE with everything combined.

Steps for "Tell me everything about John Wick":
1. Call `archivist` → get character profile
2. Call `ledger` → get markers and reputation
3. Call `timeline` → get current location and world state
4. Transfer to `narrator` with results from all three steps above

Do NOT transfer to narrator after step 1 or 2. Wait until all data is collected.

### Path C — Situation query
Query asks about the current state of things ("what's going on", "is it safe",
"situation report") → call `timeline` → transfer to narrator.

## Hard Rules

- Call each tool AT MOST ONCE per query.
- Do NOT call archivist twice. Decide once, call once.
- Do NOT transfer to narrator until you have ALL the data the query needs.
- Do NOT answer the player yourself. narrator does that.
- If you realize mid-query you need another tool — call it before transferring to narrator.

## What to Tell Narrator
When transferring, summarize what you collected:
"Character: [name]. Data from: [archivist/ledger/timeline]. Key flags: [excommunicado, alert level 8, outstanding markers, etc.]"
""",
    tools=[
        archivist_tool,
        ledger_tool,
        timeline_tool,
    ],
    sub_agents=[
        narrator_agent,
    ],
)


# ── TEST_QUERIES ──────────────────────────────────────────────────────────────
# Not used at runtime — just documentation for your testing session.
# Copy-paste these into adk web to verify each routing path.

TEST_QUERIES = {
    "archivist_routing": [
        "Who is Winston Scott?",
        "Tell me about Charon.",
        "What is the law of sanctuary?",
        "What do we know about the Baba Yaga?",
        "What happened to Santino D'Antonio?",
    ],
    "ledger_routing": [
        "Does John Wick owe anyone a marker?",
        "What is Sofia's reputation score?",
        "Who holds markers on John?",
        "What's John's relationship with Winston?",
        "What are the outstanding blood oaths right now?",
    ],
    "timeline_routing": [
        "What's happening right now?",
        "Where is John Wick?",
        "Where is the Adjudicator?",
        "What's the current crisis level?",
        "Any dangerous situations I should know about?",
    ],
    "multi_agent": [
        "Tell me everything about John Wick — who he is, what he owes, and where he is.",
        "Should I let Sofia check in? What's her standing?",
        "Is it safe to let Viktor into the hotel right now?",
    ],
    "narrator_discipline": [
        # These test that the Orchestrator NEVER answers directly —
        # all responses should come through the Narrator in rich prose.
        "What's going on?",
        "Give me the situation report.",
        "Summarize the current state of things.",
    ],
}
