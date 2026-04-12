"""
Archivist Sub-Agent — Phase 1d mock.

The hotel's memory. Handles all queries about characters, lore, rules,
and history. Returns STRUCTURED DATA only — never prose.

No database: all data is hardcoded so you can test routing without
any cloud infrastructure.
"""

from google.adk.agents import Agent
from google.adk.tools import FunctionTool

# ── Mock data store ───────────────────────────────────────────────────────────

_CHARACTERS = {
    "winston": {
        "name": "Winston Scott",
        "role": "Manager, The Continental New York",
        "reputation": 90,
        "status": "active",
        "faction": "Continental Management",
        "history": (
            "Ran the New York Continental for decades. Earned his position by "
            "navigating the transition from the old council to the High Table. "
            "Known for strict rule enforcement and quiet loyalty to old friends."
        ),
        "known_associates": ["charon", "john"],
        "marker_balance": 12,
    },
    "john": {
        "name": "John Wick",
        "role": "Freelance Assassin (formerly Tarasov organization)",
        "reputation": 99,
        "status": "excommunicado",
        "faction": "None (excommunicated)",
        "history": (
            "The Baba Yaga. Retired after completing the impossible task set by "
            "Viggo Tarasov. Returned to service when the marker held by Santino "
            "D'Antonio was called. Violated Continental grounds — excommunicated "
            "by the High Table. Last seen leaving New York."
        ),
        "known_associates": ["winston", "charon", "sofia"],
        "marker_balance": 3,
    },
    "sofia": {
        "name": "Sofia Al-Azwar",
        "role": "Manager, The Continental Casablanca",
        "reputation": 78,
        "status": "active",
        "faction": "Continental Management",
        "history": (
            "Runs the Casablanca Continental with lethal efficiency. Has a deep "
            "personal connection to John Wick — he holds a marker she has never "
            "called. Protective of her dogs above almost all else."
        ),
        "known_associates": ["john", "berrada"],
        "marker_balance": 7,
    },
    "charon": {
        "name": "Charon",
        "role": "Concierge, The Continental New York",
        "reputation": 85,
        "status": "active",
        "faction": "Continental Management",
        "history": (
            "Winston's loyal and impeccably composed concierge. Has served the "
            "Continental for over two decades. His discretion is absolute."
        ),
        "known_associates": ["winston"],
        "marker_balance": 0,
    },
    "santino": {
        "name": "Santino D'Antonio",
        "role": "High Table Member (D'Antonio crime family)",
        "reputation": 55,
        "status": "deceased",
        "faction": "High Table",
        "history": (
            "Held a blood oath marker on John Wick — the price of John's retirement. "
            "Called the marker, forcing John to assassinate his own sister, Gianna D'Antonio, "
            "to secure Santino's seat at the High Table. Subsequently placed a contract on "
            "John's life to eliminate the only witness. Killed by John Wick in the "
            "Continental's Continental Hall — a direct violation of the rules of sanctuary, "
            "which triggered John's excommunication."
        ),
        "known_associates": ["john", "gianna"],
        "marker_balance": 0,
    },
    "berrada": {
        "name": "Berrada",
        "role": "Keeper of the Elder's Books",
        "reputation": 70,
        "status": "active",
        "faction": "High Table (ancillary)",
        "history": (
            "Custodian of the records beneath the High Table. Holds information "
            "on all markers and debts. Agreed to help John reach the Elder — at "
            "a cost that has not yet been revealed."
        ),
        "known_associates": ["sofia"],
        "marker_balance": 2,
    },
}

_RULES = {
    "sanctuary": {
        "rule_number": 1,
        "title": "Law of Sanctuary",
        "text": (
            "The Continental is neutral ground. No business — meaning no acts "
            "of violence — may be conducted on hotel grounds. Violation results "
            "in immediate excommunication and forfeiture of all Continental "
            "services, worldwide."
        ),
        "precedents": [
            "Viggo Tarasov's men — excommunicated after pursuing John Wick into the bar.",
            "John Wick — excommunicated after killing Santino D'Antonio in the dining room.",
        ],
    },
    "marker": {
        "rule_number": 4,
        "title": "Law of the Marker",
        "text": (
            "A blood oath marker is a sacred and inviolable bond. When a marker "
            "is called by the holder, the debtor must fulfill it completely and "
            "without question. Failure to honor a called marker is grounds for "
            "a contract on the debtor's life, enforced by the High Table."
        ),
        "precedents": [
            "John Wick fulfilled the marker held by Santino D'Antonio — assassinating Gianna.",
        ],
    },
    "excommunicado": {
        "rule_number": 7,
        "title": "Excommunicado Protocol",
        "text": (
            "Excommunication is the severance of all Continental services: no "
            "shelter, no resources, no medical assistance, no safe passage. "
            "An excommunicado may be killed by any member of the community — "
            "in fact, a standing contract is immediately placed on their life."
        ),
        "precedents": ["John Wick — excommunicated by High Table decree."],
    },
    "coins": {
        "rule_number": 2,
        "title": "Currency of the Underworld",
        "text": (
            "Continental gold coins are the sole accepted currency for all "
            "transactions among members. They cannot be counterfeited and carry "
            "implicit weight in any negotiation."
        ),
        "precedents": [],
    },
    "high_table": {
        "rule_number": 0,
        "title": "Authority of the High Table",
        "text": (
            "The High Table is the supreme governing body of the criminal "
            "underworld. Twelve seats, each representing a major crime family. "
            "Their edicts supersede all other authority, including Continental "
            "Management. Defiance of the High Table is met with overwhelming force."
        ),
        "precedents": [
            "The Adjudicator's visit to New York — investigating rule violations.",
        ],
    },
}

_LORE_CORPUS = [
    {
        "id": "lore_01",
        "topic": "the continental origin",
        "text": (
            "The Continental Hotels are a global network of establishments that "
            "serve as neutral ground for the world's criminal elite. Entry requires "
            "membership and adherence to the rules. They function as hotel, armory, "
            "hospital, and bank simultaneously."
        ),
    },
    {
        "id": "lore_02",
        "topic": "high table composition",
        "text": (
            "The High Table is composed of twelve crime families, each holding one "
            "seat. The table convenes rarely — usually only when a major rule has "
            "been broken or an existential threat to the order exists."
        ),
    },
    {
        "id": "lore_03",
        "topic": "impossible task tarasov",
        "text": (
            "John Wick's retirement was earned through the 'impossible task' — "
            "killing three men in a single night using only a pencil, as set by "
            "Viggo Tarasov. Completing it bought his freedom from the life."
        ),
    },
    {
        "id": "lore_04",
        "topic": "baba yaga legend",
        "text": (
            "Baba Yaga is what the Russian underworld calls John Wick — not the "
            "boogeyman himself, but the one you send to kill the boogeyman. The "
            "name evokes absolute, unavoidable death. It is spoken carefully."
        ),
    },
    {
        "id": "lore_05",
        "topic": "marker blood oath creation",
        "text": (
            "A blood oath marker is created when a significant debt of honor is "
            "incurred. The debtor presses a coin bearing their blood seal. The "
            "marker physically exists as a medallion and cannot be forged."
        ),
    },
]


# ── Mock tool functions ───────────────────────────────────────────────────────


def lookup_character(name: str) -> dict:
    """
    Retrieve a full character dossier by name.

    Args:
        name: Character's common name (e.g., 'winston', 'john', 'sofia').

    Returns:
        A dict with the character's profile, or an error if unknown.
    """
    key = name.lower().strip()
    # Allow partial matches (e.g., "john wick" → "john")
    for char_key, char_data in _CHARACTERS.items():
        if key == char_key or key in char_data["name"].lower():
            return {
                "found": True,
                "source": "mock_database",
                "confidence": "high",
                "data": char_data,
                "warnings": (
                    ["Character is excommunicado — Continental services suspended."]
                    if char_data["status"] == "excommunicado"
                    else []
                ),
            }
    return {
        "found": False,
        "source": "mock_database",
        "confidence": "high",
        "data": None,
        "warnings": [f"No record found for '{name}'. Known: {', '.join(_CHARACTERS.keys())}."],
    }


def lookup_rule(topic: str) -> dict:
    """
    Look up a Continental rule or protocol by keyword.

    Args:
        topic: A keyword like 'sanctuary', 'marker', 'excommunicado', 'coins', 'high_table'.

    Returns:
        The matching rule with its precedents, or a not-found response.
    """
    topic_lower = topic.lower().strip()
    for key, rule in _RULES.items():
        if key in topic_lower or topic_lower in key or topic_lower in rule["title"].lower():
            return {
                "found": True,
                "source": "mock_database",
                "confidence": "high",
                "data": rule,
            }
    return {
        "found": False,
        "source": "mock_database",
        "confidence": "high",
        "data": None,
        "message": (f"No specific rule for '{topic}'. Try: {', '.join(_RULES.keys())}."),
    }


def search_lore(query: str) -> dict:
    """
    Search the Continental's lore archive with a free-text query.
    Returns relevant entries (mock keyword match — real version uses vector search).

    Args:
        query: A natural-language question or keyword phrase about the world.

    Returns:
        A list of matching lore entries ordered by relevance.
    """
    query_lower = query.lower()
    results = []
    for entry in _LORE_CORPUS:
        # Simple keyword overlap score
        score = sum(
            1
            for word in query_lower.split()
            if word in entry["topic"] or word in entry["text"].lower()
        )
        if score > 0:
            results.append({"score": score, **entry})

    results.sort(key=lambda x: x["score"], reverse=True)

    return {
        "found": len(results) > 0,
        "source": "mock_lore_corpus",
        "confidence": "medium" if results else "low",
        "results": results[:3],  # Top 3
        "total_found": len(results),
        "note": "Mock keyword search. Production uses hybrid vector + BM25 retrieval.",
    }


def get_character_history(name: str) -> dict:
    """
    Get the narrative history of a character — what happened to them and when.

    Args:
        name: Character name.

    Returns:
        The character's historical record with key events.
    """
    lookup = lookup_character(name)
    if not lookup["found"]:
        return lookup

    char = lookup["data"]
    return {
        "found": True,
        "source": "mock_database",
        "confidence": "high",
        "data": {
            "name": char["name"],
            "history": char["history"],
            "current_status": char["status"],
            "known_associates": char["known_associates"],
        },
    }


# ── Archivist Agent definition ────────────────────────────────────────────────

archivist_agent = Agent(
    name="archivist",
    description=(
        "Call this agent for ANY question about: who a person is, a character's background "
        "or history, hotel rules and protocols, lore, world-building facts, or anything that "
        "happened in the past. Keywords: 'who is', 'tell me about', 'what is the rule', "
        "'what happened', 'history of', 'background on', 'what do we know about'."
    ),
    model="gemini-2.5-flash",
    instruction="""You are the Archivist of The Continental Hotel — the hotel's memory.

## Your Role
You retrieve and verify factual information from the world's canon:
- Character histories and dossiers
- Hotel rules and their precedents
- Lore, traditions, and world-building details

## How You Work
1. Receive a specific query from the Orchestrator.
2. Call the appropriate tool(s) to retrieve the data.
3. Return STRUCTURED DATA only — never prose, never narrative.

## Tool Selection Guide
- "Who is X?" / "Tell me about X" → `lookup_character(name)`
- "What is the rule about X?" / "What happens if..." → `lookup_rule(topic)`
- "What do we know about X?" / "History of X" → `search_lore(query)` + `get_character_history(name)`

## Output Format
Always return a clean JSON summary of what you found:
```json
{
  "found": true,
  "source": "database | lore | both",
  "data": { ... },
  "confidence": "high | medium | low",
  "related_context": ["Additional relevant facts the Orchestrator should know"],
  "warnings": ["Inconsistencies, sensitive info, or flags"]
}
```

## Critical Rules
- NEVER fabricate lore. If you cannot find it, return found=false and say so.
- NEVER write prose. Your output is data for other agents to process.
- Flag excommunicado status immediately — it changes everything.
- If a query touches debts or markers, note that the Ledger should be consulted.
""",
    tools=[
        FunctionTool(func=lookup_character),
        FunctionTool(func=lookup_rule),
        FunctionTool(func=search_lore),
        FunctionTool(func=get_character_history),
    ],
    generate_content_config={
        "temperature": 0.2,  # Low creativity — factual retrieval only
        "max_output_tokens": 2048,
    },
)
