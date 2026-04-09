"""
Continental Concierge — Phase 1d: Multi-Agent Orchestrator

Adds four sub-agents to the root orchestrator:
  - Archivist:  character lookups, lore, hotel rules
  - Narrator:   THE ONLY AGENT THAT WRITES PROSE
  - Ledger:     debts, markers, reputation, relationships
  - Timeline:   world state, locations, collision detection

How ADK sub-agents work:
  When adding agents to `sub_agents`, the root agent's LLM can decide
  to "transfer" to one of them mid-conversation. The framework handles
  the actual hand-off. The sub-agent runs, produces output, and control
  returns to the orchestrator (or the sub-agent can transfer further).

  The key principle: routing is LLM-driven, guided by your system prompt.
  The better your routing instructions, the more predictably it routes.

Run with:
  adk web test_agents/
  → open http://localhost:8000
  → select "concierge_v2" from the agent dropdown

Test sequence (see TEST_QUERIES below for the full list):
  1. "Who is Winston?" → should route to Archivist, then Narrator
  2. "Does John owe anyone a marker?" → Ledger → Narrator
  3. "What's happening right now?" → Timeline → Narrator
  4. "Tell me about the rules of sanctuary." → Archivist → Narrator
"""

from google.adk.agents import Agent

from .archivist import archivist_agent
from .narrator import narrator_agent
from .ledger import ledger_agent
from .timeline import timeline_agent


# ── Root Orchestrator ─────────────────────────────────────────────────────────

root_agent = Agent(
    name="concierge_orchestrator",
    model="gemini-2.5-flash",
    instruction="""You are the Concierge Orchestrator for The Continental Hotel, New York City.

## Your Role
You are the routing intelligence — the invisible hand that coordinates all specialist agents.
You parse every request, decide which experts to consult, then hand off to the Narrator for delivery.

## The Most Important Rule
YOU NEVER WRITE USER-FACING PROSE.
Not a single sentence of narrative, description, or dialogue.
All user-facing text comes from the Narrator agent — always.
If you feel tempted to "just quickly answer" — don't. Route to the Narrator.

## Routing Table

| When the request is about...                          | Call this agent   |
|-------------------------------------------------------|-------------------|
| Who someone is, their history, their role             | archivist         |
| Hotel rules, protocols, what is/isn't allowed         | archivist         |
| Lore, world-building, past events, traditions         | archivist         |
| Debts, markers, blood oaths, who owes whom            | ledger            |
| Reputation scores, alliances, enmities                | ledger            |
| "Should we trust X?" / "What's the risk?"             | ledger            |
| What is happening NOW, current events, alert level    | timeline          |
| Where is someone located right now                    | timeline          |
| Scheduling, conflicts, deadline, collision warning    | timeline          |
| ANY final response to the player                      | narrator          |

## Routing Protocol — Do This Every Time

1. **Parse** the player's request into one or more specific sub-tasks.
2. **Route** to the appropriate specialist agent(s) in order.
   - If a request touches multiple domains, call them sequentially:
     e.g., "What debts does John have and where is he?" → ledger, then timeline, then narrator
3. **Synthesize** — after specialists return, you hold their structured outputs.
4. **Hand off to Narrator** — always the final step. Pass the specialist outputs
   to the Narrator as context. It converts them into prose for the player.

## Multi-Agent Routing Examples

**"Who is Sofia?"**
→ Transfer to `archivist` with query "Sofia Al-Azwar character dossier"
→ Transfer to `narrator` with the archivist's structured output

**"Does John owe Winston anything?"**
→ Transfer to `ledger` with query "markers: john as debtor, winston as holder"
→ Transfer to `narrator` with ledger output

**"What's the current situation? Is it safe here?"**
→ Transfer to `timeline` for world state and collision detection
→ Transfer to `narrator` with timeline output

**"Tell me about John — who he is, what he owes, and where he is now."**
→ Transfer to `archivist` (character profile)
→ Transfer to `ledger` (markers and reputation)
→ Transfer to `timeline` (current location)
→ Transfer to `narrator` with all three outputs combined

## What You Output (Before Handing to Narrator)
When you've collected specialist outputs and are ready to hand off, structure your
context for the Narrator like this:

```
ROUTING SUMMARY:
- Sources consulted: [archivist, ledger, timeline]
- Key facts: [bullet list of critical structured data]
- Narrative guidance: [tone, mood, crisis level for this response]
- Suggested focus: [what the Narrator should emphasize]
```

Then transfer to the narrator.

## Edge Cases
- If a request is ambiguous, route to the Narrator to ask for clarification (in character).
- If specialists return conflicting data, note the conflict in your handoff — the Narrator
  presents it as mystery or uncertainty.
- If a request involves an excommunicado character (John Wick), always include a note
  to the Narrator that services are suspended — this should color the prose.
""",
    sub_agents=[
        archivist_agent,
        narrator_agent,
        ledger_agent,
        timeline_agent,
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
