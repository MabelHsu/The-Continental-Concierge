"""
Timeline Sub-Agent — Phase 1d mock.

Temporal and spatial consistency engine. Tracks where everyone is,
what just happened, and flags collisions (schedule conflicts, hostile
co-presence, deadline breaches).

No database: hardcoded state that evolves as you test.
"""

from google.adk.agents import Agent
from google.adk.tools import FunctionTool


# ── Mutable world state ───────────────────────────────────────────────────────
# Using a dict so tools can modify it during a session (simulates DB writes).

_WORLD_STATE = {
    "current_day": 1,
    "current_phase": "evening",  # dawn | morning | afternoon | evening | night | midnight
    "phase_order": ["dawn", "morning", "afternoon", "evening", "night", "midnight"],
    "continental_status": "open",
    "alert_level": 8,  # 1-10
}

_LOCATIONS = {
    "winston": {"location": "The Continental, New York — Manager's Office", "since_phase": "afternoon"},
    "john": {"location": "The Continental, New York — Lobby", "since_phase": "evening"},
    "sofia": {"location": "Casablanca Continental — Manager's Suite", "since_phase": "morning"},
    "charon": {"location": "The Continental, New York — Front Desk", "since_phase": "dawn"},
    "berrada": {"location": "Unknown — last seen Casablanca Medina", "since_phase": "morning"},
    "the adjudicator": {"location": "The Continental, New York — Meeting Room 3", "since_phase": "afternoon"},
}

_EVENT_LOG = [
    {"day": 0, "phase": "dawn", "type": "excommunicado_decree", "description": "High Table issues excommunicado decree against John Wick. All Continental services suspended worldwide.", "characters": ["john", "high_table"]},
    {"day": 0, "phase": "morning", "type": "contract_posted", "description": "Open contract on John Wick posted — 14 million gold. Any operator may collect.", "characters": ["john", "high_table"]},
    {"day": 0, "phase": "afternoon", "type": "adjudicator_arrival", "description": "The Adjudicator arrives at the Continental New York to investigate rule violations.", "characters": ["the adjudicator", "winston"]},
    {"day": 1, "phase": "evening", "type": "current", "description": "John Wick present in the Continental lobby. Excommunication technically bars him, but no action taken yet.", "characters": ["john", "charon"]},
]

_DEADLINES = [
    {"id": "dl001", "title": "John Wick contract", "description": "Open contract remains active until fulfilled or rescinded.", "deadline_day": None, "deadline_phase": None, "urgency": "high", "characters": ["john"]},
    {"id": "dl002", "title": "Adjudicator ruling", "description": "The Adjudicator must deliver her ruling on Winston within 48 hours of arriving.", "deadline_day": 3, "deadline_phase": "afternoon", "urgency": "critical", "characters": ["the adjudicator", "winston"]},
    {"id": "dl003", "title": "Marker: John → Winston", "description": "Winston's marker on John has no stated deadline, but tensions are escalating.", "deadline_day": None, "deadline_phase": None, "urgency": "medium", "characters": ["john", "winston"]},
]


# ── Mock tool functions ───────────────────────────────────────────────────────

def get_world_state() -> dict:
    """
    Return the current state of the world: time, crisis level, Continental status.

    Returns:
        Current world state including day, phase, alert level, and open contracts.
    """
    return {
        **_WORLD_STATE,
        "open_contracts": [
            {"target": "John Wick", "value": "14 million gold", "status": "open", "posted_by": "High Table"},
        ],
        "active_events": [
            "Adjudicator present — all Continental management under review.",
            "John Wick's excommunication in effect since dawn.",
            "High Table summit convened — political pressure extreme.",
        ],
    }


def get_current_locations(characters: list = None) -> dict:
    """
    Get the current known locations of characters.

    Args:
        characters: Optional list of character names. If None, returns all.

    Returns:
        Location data for each requested character.
    """
    if characters is None:
        return {"locations": _LOCATIONS, "as_of": f"Day {_WORLD_STATE['current_day']}, {_WORLD_STATE['current_phase']}"}

    result = {}
    for name in characters:
        key = name.lower()
        result[key] = _LOCATIONS.get(key, {"location": "unknown", "since_phase": "unknown"})
    return {"locations": result, "as_of": f"Day {_WORLD_STATE['current_day']}, {_WORLD_STATE['current_phase']}"}


def get_recent_events(day: int = None, phase: str = None, character: str = None, limit: int = 5) -> dict:
    """
    Query the event log with optional filters.

    Args:
        day: Filter by day number. None for all days.
        phase: Filter by time phase (dawn, morning, etc.). None for all.
        character: Filter by character involved. None for all.
        limit: Maximum events to return (default 5).

    Returns:
        Filtered event log, most recent first.
    """
    events = _EVENT_LOG.copy()

    if day is not None:
        events = [e for e in events if e["day"] == day]
    if phase is not None:
        events = [e for e in events if e["phase"] == phase]
    if character is not None:
        char_key = character.lower()
        events = [e for e in events if char_key in [c.lower() for c in e["characters"]]]

    events.reverse()  # Most recent first
    return {
        "events": events[:limit],
        "total_matching": len(events),
        "filters_applied": {"day": day, "phase": phase, "character": character},
    }


def detect_collisions() -> dict:
    """
    Scan for dangerous situations: hostile co-presence, deadline breaches,
    scheduling conflicts, or rule violations about to occur.

    Returns:
        All detected collisions with severity scores.
    """
    collisions = []

    # Check: excommunicado on Continental grounds
    john_loc = _LOCATIONS.get("john", {})
    if "continental" in john_loc.get("location", "").lower():
        collisions.append({
            "type": "excommunicado_on_grounds",
            "severity": 9,
            "details": "John Wick (excommunicado) is physically present in The Continental. This is a direct rule violation.",
            "characters": ["john"],
            "implied_rule": "Excommunicado may not use Continental services or grounds.",
        })

    # Check: Adjudicator + Winston in same location
    adj_loc = _LOCATIONS.get("the adjudicator", {})
    win_loc = _LOCATIONS.get("winston", {})
    if "continental, new york" in adj_loc.get("location", "").lower() and \
       "continental, new york" in win_loc.get("location", "").lower():
        collisions.append({
            "type": "investigation_in_progress",
            "severity": 7,
            "details": "The Adjudicator and Winston are in the same building. The investigation is live.",
            "characters": ["the adjudicator", "winston"],
            "implied_rule": "High Table investigation supersedes Continental management authority.",
        })

    # Check: upcoming deadlines
    for dl in _DEADLINES:
        if dl["urgency"] == "critical":
            collisions.append({
                "type": "critical_deadline",
                "severity": 8,
                "details": f"DEADLINE: {dl['title']} — {dl['description']}",
                "characters": dl["characters"],
            })

    return {
        "collision_count": len(collisions),
        "collisions": sorted(collisions, key=lambda x: x["severity"], reverse=True),
        "highest_severity": max((c["severity"] for c in collisions), default=0),
        "recommendation": "Escalate to management immediately." if any(c["severity"] >= 8 for c in collisions) else "Monitor.",
    }


def get_upcoming_deadlines(urgency: str = None) -> dict:
    """
    List upcoming obligations and deadlines.

    Args:
        urgency: Filter by 'low', 'medium', 'high', or 'critical'. None for all.

    Returns:
        Deadlines sorted by urgency, with time remaining where known.
    """
    deadlines = _DEADLINES.copy()
    if urgency:
        deadlines = [d for d in deadlines if d["urgency"] == urgency]
    return {
        "deadlines": deadlines,
        "critical_count": len([d for d in deadlines if d["urgency"] == "critical"]),
        "as_of": f"Day {_WORLD_STATE['current_day']}, {_WORLD_STATE['current_phase']}",
    }


# ── Timeline Agent definition ─────────────────────────────────────────────────

timeline_agent = Agent(
    name="timeline",
    model="gemini-2.5-flash",
    instruction="""You are the Timeline Agent — you track what is happening where and when.

## Your Role
You maintain temporal and spatial consistency for The Continental:
- **Where is everyone?** Real-time character location tracking.
- **What happened when?** The event log — the authoritative record.
- **Collision detection**: Hostile co-presence, deadline breaches, rule conflicts.
- **World state**: Current day, phase, alert level, active crises.

## How You Work
1. Receive a query or action from the Orchestrator.
2. For **queries**: call the relevant lookup tool.
3. Always run `detect_collisions()` when the query involves movement or major events.
4. Return STRUCTURED DATA — no prose, no narrative.

## Tool Selection Guide
- "What's happening?" / "Current situation?" → `get_world_state()`
- "Where is X?" / "Who is at the Continental?" → `get_current_locations(characters)`
- "What happened today?" / "Events involving X?" → `get_recent_events(day, character)`
- "Any conflicts? Any danger?" → `detect_collisions()`
- "What deadlines are coming?" → `get_upcoming_deadlines(urgency)`

## Output Format
```json
{
  "action": "query",
  "data": { ... },
  "collisions_detected": [
    {"type": "collision_type", "severity": 1-10, "details": "..."}
  ],
  "world_state_summary": {
    "day": 1,
    "phase": "evening",
    "alert_level": 8,
    "critical_issues": ["list of most urgent things"]
  }
}
```

## Collision Types to Flag
- `excommunicado_on_grounds` — severity 9: immediate rule violation
- `hostile_presence` — severity 7-9: enemies in same location
- `investigation_in_progress` — severity 7: Adjudicator active
- `critical_deadline` — severity 8: deadline imminent
- `temporal_paradox` — severity 10: timeline contradiction detected

## Rules
- NEVER fabricate event data. Log events as they occur.
- Any collision with severity ≥ 8 must be escalated to the Orchestrator immediately.
- Always include `world_state_summary` in your response — the Narrator needs it for atmosphere.
""",
    tools=[
        FunctionTool(func=get_world_state),
        FunctionTool(func=get_current_locations),
        FunctionTool(func=get_recent_events),
        FunctionTool(func=detect_collisions),
        FunctionTool(func=get_upcoming_deadlines),
    ],
    generate_content_config={
        "temperature": 0.2,
        "max_output_tokens": 2048,
    },
)
