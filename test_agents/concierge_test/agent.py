"""
Minimal Continental Concierge — Phase 1 test agent.

No database, no sub-agents, no cloud infra required.
Just the Orchestrator prompt + mock FunctionTools that return hardcoded data.
Run with:  adk web test_agents/
"""

from google.adk.agents import Agent
from google.adk.tools import FunctionTool


# ── Mock tool implementations ────────────────────────────────────────────────

def lookup_character(name: str) -> dict:
    """Look up a character by name. Returns their profile from The Continental."""
    characters = {
        "winston": {
            "name": "Winston Scott",
            "role": "Manager of The Continental, New York",
            "reputation": 90,
            "status": "active",
            "marker_balance": 12,
            "notes": "Runs the New York Continental with strict adherence to the rules.",
        },
        "sofia": {
            "name": "Sofia Al-Azwar",
            "role": "Manager of The Continental, Casablanca",
            "reputation": 78,
            "status": "active",
            "marker_balance": 7,
            "notes": "Known for her lethal efficiency and loyalty.",
        },
        "charon": {
            "name": "Charon",
            "role": "Concierge, The Continental New York",
            "reputation": 85,
            "status": "active",
            "marker_balance": 0,
            "notes": "Winston's loyal and impeccably composed concierge.",
        },
        "john": {
            "name": "John Wick",
            "role": "Freelance Assassin",
            "reputation": 99,
            "status": "excommunicado",
            "marker_balance": 3,
            "notes": "The Baba Yaga. Excommunicated following the events on Continental grounds.",
        },
    }
    return characters.get(
        name.lower(),
        {"error": f"Unknown character: {name}. Known characters: {', '.join(characters.keys())}"},
    )


def check_marker(debtor: str, holder: str) -> dict:
    """Check if a blood oath marker exists between two characters."""
    markers = [
        {"debtor": "john", "holder": "santino", "status": "called", "description": "Marker called to assassinate Gianna D'Antonio."},
        {"debtor": "john", "holder": "winston", "status": "outstanding", "description": "Marker for services rendered during the NY events."},
        {"debtor": "sofia", "holder": "john", "status": "outstanding", "description": "Marker from John helping Sofia reach Elder."},
    ]
    d, h = debtor.lower(), holder.lower()
    for m in markers:
        if m["debtor"] == d and m["holder"] == h:
            return m
    return {
        "result": "no_marker",
        "message": f"No marker found between debtor '{debtor}' and holder '{holder}'.",
    }


def get_world_state() -> dict:
    """Return the current state of The Continental world: time, active events, open contracts."""
    return {
        "current_day": 1,
        "current_phase": "evening",
        "location": "The Continental Hotel, New York",
        "active_events": [
            "High Table summit convened — all contracts temporarily suspended",
            "John Wick's excommunication in effect since dawn",
        ],
        "open_contracts": [
            {"target": "John Wick", "value": "14 million", "status": "open", "posted_by": "High Table"},
        ],
        "continental_status": "open",
        "alert_level": "critical",
    }


def lookup_rule(topic: str) -> dict:
    """Look up a Continental rule or protocol by topic keyword."""
    rules = {
        "marker": "A blood oath marker is a sacred bond. When called, the debtor must fulfill it or face death.",
        "sanctuary": "The Continental is neutral ground. No business — meaning no killing — may be conducted on hotel grounds.",
        "excommunicado": "Excommunication severs all Continental services. No shelter, no resources, no assistance of any kind.",
        "coins": "Continental gold coins are the currency of the underworld. They are used for all transactions between members.",
        "high_table": "The High Table is the governing body of the criminal underworld. Twelve seats, each representing a major crime family.",
        "adjudicator": "The Adjudicator acts as the High Table's enforcement arm, investigating and punishing rule violations.",
    }
    topic_lower = topic.lower()
    for key, text in rules.items():
        if key in topic_lower or topic_lower in key:
            return {"rule": key, "description": text}
    return {
        "result": "not_found",
        "message": f"No specific rule found for '{topic}'. Try: marker, sanctuary, excommunicado, coins, high_table, adjudicator.",
    }


# ── Root Agent ───────────────────────────────────────────────────────────────

root_agent = Agent(
    name="concierge_test",
    model="gemini-2.0-flash",
    instruction="""You are the Concierge at The Continental Hotel — the legendary establishment that serves as neutral ground for the world's top assassins.

Your role is to assist guests with information about characters, markers, rules, and the current state of the world. You are impeccably composed, formal, and discreet.

When answering questions:
- Use your tools to look up accurate information before responding
- Speak in the polished, understated tone of a high-end hotel concierge
- Reference lore naturally — you know this world intimately
- If asked about characters, always call lookup_character first
- If asked about rules or protocols, call lookup_rule
- If asked about markers or debts, call check_marker with both parties
- If asked about current events or the state of things, call get_world_state

Example exchanges:
- "Who is Winston?" → call lookup_character("winston") → respond with his profile in character
- "What happened to John Wick?" → call lookup_character("john") + get_world_state() → weave the answer
- "Can I conduct business here?" → call lookup_rule("sanctuary") → explain the rule politely but firmly
""",
    tools=[
        FunctionTool(func=lookup_character),
        FunctionTool(func=check_marker),
        FunctionTool(func=get_world_state),
        FunctionTool(func=lookup_rule),
    ],
)
