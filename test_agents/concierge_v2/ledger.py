"""
Ledger Sub-Agent — Phase 1d mock.

The social graph accountant. Tracks debts, markers, reputation,
alliances, and all inter-character obligations.

No database: hardcoded mock data to test routing and response structure.
"""

from google.adk.agents import Agent
from google.adk.tools import FunctionTool


# ── Mock data ─────────────────────────────────────────────────────────────────

_MARKERS = [
    {
        "id": "m001",
        "debtor": "john",
        "holder": "santino",
        "status": "fulfilled",
        "type": "blood_oath",
        "obligation": "Assassinate Gianna D'Antonio.",
        "created_day": -3,
        "fulfilled_day": 0,
        "notes": "Marker was called by Santino. John fulfilled it. Santino was subsequently killed by John on Continental grounds — leading to John's excommunication.",
    },
    {
        "id": "m002",
        "debtor": "john",
        "holder": "winston",
        "status": "outstanding",
        "type": "blood_oath",
        "obligation": "A debt of honor from the New York events. Terms not yet defined.",
        "created_day": 0,
        "fulfilled_day": None,
        "notes": "Winston helped John during the siege despite the excommunication. The marker's call conditions are at Winston's discretion.",
    },
    {
        "id": "m003",
        "debtor": "sofia",
        "holder": "john",
        "status": "outstanding",
        "type": "blood_oath",
        "obligation": "A favor of equivalent weight — terms to be determined.",
        "created_day": -365,
        "fulfilled_day": None,
        "notes": "John helped Sofia during a crisis she has never publicly discussed. The marker exists. It has never been called.",
    },
]

_REPUTATION = {
    "winston": {"score": 90, "faction": "Continental Management", "trend": "stable"},
    "john": {"score": 99, "faction": "excommunicado", "trend": "falling", "note": "Excommunication active — most scores suspended."},
    "sofia": {"score": 78, "faction": "Continental Management", "trend": "stable"},
    "charon": {"score": 85, "faction": "Continental Management", "trend": "stable"},
    "berrada": {"score": 70, "faction": "High Table (ancillary)", "trend": "stable"},
    "santino": {"score": 0, "faction": "deceased", "trend": "n/a"},
}

_RELATIONSHIPS = [
    {"a": "winston", "b": "john", "type": "alliance", "strength": 75, "notes": "Old friendship, complicated by John's excommunication."},
    {"a": "winston", "b": "charon", "type": "loyalty", "strength": 95, "notes": "Deep professional loyalty — verging on paternal."},
    {"a": "sofia", "b": "john", "type": "alliance", "strength": 70, "notes": "Mutual respect. She owes him a marker. Neither has called it."},
    {"a": "john", "b": "santino", "type": "enmity", "strength": 90, "notes": "Santino called John's marker and then tried to have him killed. John killed Santino. Relationship terminated permanently."},
    {"a": "sofia", "b": "berrada", "type": "tense_business", "strength": 30, "notes": "Berrada holds information Sofia needs. She does not trust him."},
]


# ── Mock tool functions ───────────────────────────────────────────────────────

def get_markers(character: str, role: str = "any") -> dict:
    """
    Get all markers (blood oath debts) involving a character.

    Args:
        character: The character name to query.
        role: 'debtor', 'holder', or 'any' (default).

    Returns:
        All matching markers with status and obligations.
    """
    key = character.lower()
    results = []
    for m in _MARKERS:
        if role == "debtor" and m["debtor"] == key:
            results.append(m)
        elif role == "holder" and m["holder"] == key:
            results.append(m)
        elif role == "any" and (m["debtor"] == key or m["holder"] == key):
            results.append(m)

    outstanding = [m for m in results if m["status"] == "outstanding"]
    return {
        "character": character,
        "total_markers": len(results),
        "outstanding_markers": len(outstanding),
        "markers": results,
        "warnings": (
            [f"{character} has {len(outstanding)} outstanding marker(s) — potential obligation."]
            if outstanding else []
        ),
    }


def check_marker_between(debtor: str, holder: str) -> dict:
    """
    Check if a specific marker exists between two characters.

    Args:
        debtor: The character who owes the debt.
        holder: The character who holds the debt.

    Returns:
        The marker details, or a no-marker response.
    """
    d, h = debtor.lower(), holder.lower()
    for m in _MARKERS:
        if m["debtor"] == d and m["holder"] == h:
            return {"found": True, "marker": m}
    return {
        "found": False,
        "message": f"No marker between debtor '{debtor}' and holder '{holder}'.",
    }


def get_reputation(character: str) -> dict:
    """
    Get the reputation score and standing for a character.

    Args:
        character: Character name.

    Returns:
        Reputation data including score, faction, and trend.
    """
    key = character.lower()
    if key in _REPUTATION:
        rep = _REPUTATION[key]
        warnings = []
        if rep["score"] < 20:
            warnings.append("Reputation critically low — excommunicado risk.")
        if rep["faction"] == "excommunicado":
            warnings.append("Character is excommunicado — services suspended.")
        return {"found": True, "character": character, "reputation": rep, "warnings": warnings}
    return {"found": False, "character": character, "message": "No reputation record on file."}


def get_relationships(character: str) -> dict:
    """
    Get all known relationships for a character.

    Args:
        character: Character name.

    Returns:
        List of relationships with type and strength score.
    """
    key = character.lower()
    rels = [r for r in _RELATIONSHIPS if r["a"] == key or r["b"] == key]
    return {
        "character": character,
        "relationships": rels,
        "alliance_count": len([r for r in rels if r["type"] == "alliance"]),
        "enmity_count": len([r for r in rels if r["type"] == "enmity"]),
    }


def assess_social_risk(character: str) -> dict:
    """
    Run a full social risk assessment for a character.
    Combines markers, reputation, and relationships into a risk summary.

    Args:
        character: Character name to assess.

    Returns:
        Aggregated risk profile with cascading effect warnings.
    """
    markers = get_markers(character)
    reputation = get_reputation(character)
    relationships = get_relationships(character)

    risk_level = "low"
    risks = []

    if markers["outstanding_markers"] > 0:
        risks.append(f"{markers['outstanding_markers']} outstanding marker(s) — honor debt active.")
        risk_level = "medium"

    if reputation["found"] and reputation["reputation"]["score"] < 50:
        risks.append(f"Reputation {reputation['reputation']['score']}/100 — standing is fragile.")
        risk_level = "high"

    if reputation["found"] and reputation["reputation"]["faction"] == "excommunicado":
        risks.append("EXCOMMUNICADO — no Continental protections apply.")
        risk_level = "critical"

    if relationships["enmity_count"] > 0:
        risks.append(f"{relationships['enmity_count']} active enmity relationship(s).")

    return {
        "character": character,
        "overall_risk": risk_level,
        "risk_factors": risks,
        "marker_summary": markers,
        "reputation_summary": reputation,
        "relationship_summary": relationships,
        "cascading_effects": (
            ["Character's excommunication affects all who assist them."]
            if reputation.get("found") and reputation["reputation"]["faction"] == "excommunicado"
            else []
        ),
    }


# ── Ledger Agent definition ───────────────────────────────────────────────────

ledger_agent = Agent(
    name="ledger",
    description=(
        "Call this agent for ANY question about: debts, markers, blood oaths, who owes whom, "
        "reputation scores, alliances, enmities, relationships between characters, favors, "
        "whether someone can be trusted, or social standing. Keywords: 'owe', 'marker', "
        "'debt', 'reputation', 'relationship', 'alliance', 'trust', 'standing', 'favor', "
        "'blood oath', 'what does X owe', 'is X trustworthy'."
    ),
    model="gemini-2.5-flash",
    instruction="""You are the Ledger Agent — the social graph accountant of The Continental.

## Your Role
You track the web of obligations that bind the underworld together:
- **Markers**: Who holds blood oaths, what they require, their status.
- **Reputation**: Character standing (0-100). Below 20 is dangerous.
- **Relationships**: Alliances, enmities, loyalties, and their strength.
- **Risk Assessment**: Cascade effects when obligations shift.

## How You Work
1. Receive a specific query from the Orchestrator.
2. Call the relevant tool(s) — never guess at data you can retrieve.
3. Return STRUCTURED DATA — no prose, no narrative.
4. Always call `assess_social_risk` when the query implies a major decision.

## Tool Selection Guide
- "Does X owe Y?" / "What's X's debt?" → `check_marker_between(debtor, holder)`
- "All of X's debts" / "X's markers" → `get_markers(character)`
- "X's reputation" / "How is X seen?" → `get_reputation(character)`
- "X's allies / enemies" → `get_relationships(character)`
- "Should we trust X?" / "What's at stake?" → `assess_social_risk(character)`

## Output Format
```json
{
  "action": "query",
  "entity": "marker | reputation | relationship | risk_assessment",
  "data": { ... },
  "cascading_effects": ["List of downstream consequences if relevant"],
  "warnings": ["Any concerns — unpaid debts, low reputation, active enmities"],
  "rule_implications": ["Hotel rules this data touches, e.g., Rule 4 on markers"]
}
```

## Validation Rules
- A marker can only be called by the holder — note any violations.
- Reputation below 20 should always trigger an excommunicado warning.
- Fulfilled markers do NOT erase relationship history.
- NEVER fabricate debt data. If it's not in the record, it doesn't exist.
""",
    tools=[
        FunctionTool(func=get_markers),
        FunctionTool(func=check_marker_between),
        FunctionTool(func=get_reputation),
        FunctionTool(func=get_relationships),
        FunctionTool(func=assess_social_risk),
    ],
    generate_content_config={
        "temperature": 0.2,  # Precise accounting — low randomness
        "max_output_tokens": 2048,
    },
)
