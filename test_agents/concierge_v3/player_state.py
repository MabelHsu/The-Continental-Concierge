"""
Mock Player State — Phase 1d test layer.

Replaces AlloyDB for local testing. A module-level dict acts as the
"database" — it persists across tool calls within a session, so the
onboarding flow actually accumulates state turn by turn.

## How to control the test scenario

Change the two toggles at the top of this file:

  MOCK_ONBOARDING_COMPLETE = False   → starts at the hotel lobby, no identity
  MOCK_ONBOARDING_COMPLETE = True    → skips onboarding, goes straight to gameplay

  MOCK_PATH = "mystery"              → 5-step identity reveal
  MOCK_PATH = "custom"               → 4-step guided creation
"""

from typing import Optional

# ── TEST CONFIGURATION ────────────────────────────────────────────────────────
# Change these to switch scenarios without touching any other file.

MOCK_ONBOARDING_COMPLETE = False  # Set True to skip onboarding

MOCK_PATH = "mystery"  # "mystery" | "custom" — only used when False above


# ── Live state dict ───────────────────────────────────────────────────────────
# Mutable across the session. Simulates player_characters + player_status_view.

_STATE: dict = {
    # Identity
    "session_id": "test-session-001",
    "name": None,
    "alias": None,
    "title": None,
    "archetype": None,
    "backstory": None,
    # Onboarding
    "onboarding_complete": MOCK_ONBOARDING_COMPLETE,
    "creation_path": "custom" if MOCK_ONBOARDING_COMPLETE else MOCK_PATH,
    "onboarding_step": 5 if MOCK_ONBOARDING_COMPLETE else 0,
    "identity_revealed": MOCK_ONBOARDING_COMPLETE,
    "identity_clues": [],
    # Stats
    "reputation": 55 if MOCK_ONBOARDING_COMPLETE else 50,
    "combat_rating": 50,
    "influence": 30,
    "gold_coins": 7,
    # World position
    "faction_name": "Independent" if MOCK_ONBOARDING_COMPLETE else None,
    "current_location": "Continental Hotel Lobby",
    "is_continental": True,
    "status": "active",
    # Missions
    "active_mission_title": None,
    "active_mission_type": None,
    "missions_completed": 0,
    "missions_failed": 0,
    # Inventory — pre-seeded if onboarding is bypassed
    "inventory": (
        [
            {"name": "Suppressed Pistol", "type": "weapon", "quantity": 1},
            {"name": "Clean Passport", "type": "document", "quantity": 1},
        ]
        if MOCK_ONBOARDING_COMPLETE
        else []
    ),
    "faction_standings": (
        [
            {"faction": "The Continental", "standing": 70},
            {"faction": "High Table", "standing": 50},
            {"faction": "Bowery King's Network", "standing": 45},
            {"faction": "Tarasov Organization", "standing": 30},
        ]
        if MOCK_ONBOARDING_COMPLETE
        else []
    ),
}

# Backfill name/alias when starting in complete mode
if MOCK_ONBOARDING_COMPLETE:
    _STATE["name"] = "Ghost"
    _STATE["alias"] = "Ghost"
    _STATE["archetype"] = "assassin"


# ── Mock available missions ────────────────────────────────────────────────────

_MISSIONS = [
    {
        "id": 1,
        "title": "The Osaka Arrangement",
        "mission_type": "elimination",
        "description": (
            "A guest requires that an outstanding matter be concluded before "
            "the High Table convenes. The subject is in Osaka. "
            "Time is a factor."
        ),
        "priority": 4,
        "requested_by": "Anonymous",
        "requester_faction": "High Table (ancillary)",
        "deadline_day": 3,
        "deadline_phase": "midnight",
        "requirements": {"min_reputation": 40},
    },
    {
        "id": 2,
        "title": "A Package, Discreetly Moved",
        "mission_type": "transport",
        "description": (
            "Certain materials require quiet relocation from one borough "
            "to another. No questions. No complications."
        ),
        "priority": 2,
        "requested_by": "Bowery King",
        "requester_faction": "Bowery King's Network",
        "deadline_day": 2,
        "deadline_phase": "dawn",
        "requirements": {"min_reputation": 20},
    },
    {
        "id": 3,
        "title": "The Casablanca Fragment",
        "mission_type": "information_retrieval",
        "description": (
            "A piece of information that should not exist, held by someone "
            "who should not have it. Recovery required. Discretion essential."
        ),
        "priority": 3,
        "requested_by": "Sofia Al-Azwar",
        "requester_faction": "Continental Management",
        "deadline_day": 4,
        "deadline_phase": "evening",
        "requirements": {"min_reputation": 50},
    },
]


# ── Tool functions ─────────────────────────────────────────────────────────────
# These are registered as FunctionTools on the orchestrator and onboarding agent.
# Because they operate on the module-level _STATE dict, state persists across calls.


def get_player(session_id: str = "test-session-001") -> dict:
    """
    Get the current player character state.

    Returns the full player status including onboarding progress, stats,
    inventory, and active mission. Returns None-equivalent if no player exists.

    Args:
        session_id: The session identifier (use 'test-session-001' for testing).

    Returns:
        Full player state dict. Check onboarding_complete before routing.
    """
    return dict(_STATE)


def update_player(
    session_id: str = "test-session-001",
    name: Optional[str] = None,
    alias: Optional[str] = None,
    archetype: Optional[str] = None,
    faction_name: Optional[str] = None,
    backstory: Optional[str] = None,
    onboarding_step: Optional[int] = None,
    identity_clue: Optional[str] = None,
) -> dict:
    """
    Update player character fields during onboarding.

    Called by the Onboarding Agent after each Charon exchange to persist
    extracted data. Only updates fields that are not None.

    Args:
        session_id: The session (use 'test-session-001' for testing).
        name: Player's real name (set on custom path or mystery revelation).
        alias: Working alias used before full identity reveal.
        archetype: Role — assassin, cleaner, fixer, information_broker,
                   weapons_dealer, driver, medic, enforcer.
        faction_name: Primary faction affiliation.
        backstory: Brief origin story (mystery path: assembled from clues).
        onboarding_step: Current step number (advances 1 per exchange).
        identity_clue: One new clue to append to identity_clues list
                       (mystery path only).

    Returns:
        Updated player state dict.
    """
    if name is not None:
        _STATE["name"] = name
    if alias is not None:
        _STATE["alias"] = alias
    if archetype is not None:
        _STATE["archetype"] = archetype
    if faction_name is not None:
        _STATE["faction_name"] = faction_name
    if backstory is not None:
        _STATE["backstory"] = backstory
    if onboarding_step is not None:
        _STATE["onboarding_step"] = onboarding_step
    if identity_clue is not None:
        _STATE["identity_clues"].append(identity_clue)
    return dict(_STATE)


def complete_onboarding(session_id: str = "test-session-001") -> dict:
    """
    Finalise onboarding: mark complete, reveal identity, seed inventory.

    Called by the Onboarding Agent on the final step of either path.
    After this, the orchestrator routes all messages through the full
    gameplay loop instead of returning to Charon.

    Args:
        session_id: The session (use 'test-session-001' for testing).

    Returns:
        Completed player state dict.
    """
    _STATE["onboarding_complete"] = True
    _STATE["identity_revealed"] = True

    # Seed inventory by archetype
    archetype = _STATE.get("archetype") or "assassin"
    _STATE["inventory"] = _starting_inventory(archetype)

    # Seed basic faction standings
    _STATE["faction_standings"] = [
        {"faction": "The Continental", "standing": 70},
        {"faction": "High Table", "standing": 50},
        {"faction": "Bowery King's Network", "standing": 45},
        {"faction": "Tarasov Organization", "standing": 30},
    ]

    return dict(_STATE)


def get_available_missions(
    session_id: str = "test-session-001",
    limit: int = 3,
) -> list:
    """
    Return missions available to this player, filtered by reputation.

    Args:
        session_id: The session (use 'test-session-001' for testing).
        limit: Max missions to return (default 3).

    Returns:
        List of available mission dicts ordered by priority.
    """
    rep = _STATE.get("reputation", 50)
    available = [m for m in _MISSIONS if m["requirements"].get("min_reputation", 0) <= rep]
    return available[:limit]


def accept_mission(
    session_id: str = "test-session-001",
    mission_id: int = 1,
) -> dict:
    """
    Assign a mission to the player.

    Args:
        session_id: The session.
        mission_id: ID of the mission to accept (from get_available_missions).

    Returns:
        Updated player state with active mission set.
    """
    if _STATE.get("active_mission_title"):
        return {"error": "You already have an active mission. Resolve it first."}

    mission = next((m for m in _MISSIONS if m["id"] == mission_id), None)
    if not mission:
        return {"error": f"Mission {mission_id} not found."}

    _STATE["active_mission_title"] = mission["title"]
    _STATE["active_mission_type"] = mission["mission_type"]
    return dict(_STATE)


def complete_mission(
    session_id: str = "test-session-001",
    outcome: str = "success",
) -> dict:
    """
    Resolve the player's active mission and apply rewards/consequences.

    Args:
        session_id: The session.
        outcome: 'success' | 'failure' | 'complicated'

    Returns:
        Resolution dict with rewards and updated player state.
    """
    if not _STATE.get("active_mission_title"):
        return {"error": "No active mission."}

    rewards = {}
    if outcome == "success":
        gold = 5
        rep_delta = 10
        _STATE["gold_coins"] += gold
        _STATE["reputation"] = min(100, _STATE["reputation"] + rep_delta)
        _STATE["missions_completed"] += 1
        rewards = {"gold": gold, "reputation": f"+{rep_delta}"}
    elif outcome == "failure":
        rep_delta = -8
        _STATE["reputation"] = max(0, _STATE["reputation"] + rep_delta)
        _STATE["missions_failed"] += 1
        rewards = {"reputation": str(rep_delta)}
    else:  # complicated
        rep_delta = -3
        _STATE["reputation"] = max(0, _STATE["reputation"] + rep_delta)
        _STATE["missions_completed"] += 1
        rewards = {"reputation": str(rep_delta)}

    _STATE["active_mission_title"] = None
    _STATE["active_mission_type"] = None
    return {"outcome": outcome, "rewards": rewards, "player": dict(_STATE)}


# ── Internal helpers ───────────────────────────────────────────────────────────


def _starting_inventory(archetype: str) -> list:
    kits = {
        "assassin": [
            {"name": "Suppressed Pistol", "type": "weapon", "quantity": 1},
            {"name": "Clean Passport", "type": "document", "quantity": 1},
        ],
        "cleaner": [
            {"name": "Burner Phone", "type": "artifact", "quantity": 1},
            {"name": "Continental Coin", "type": "token", "quantity": 7},
        ],
        "fixer": [
            {"name": "Contact List", "type": "intel", "quantity": 1},
            {"name": "Blank Marker", "type": "document", "quantity": 1},
        ],
        "information_broker": [
            {"name": "Dossier Fragment", "type": "intel", "quantity": 1},
            {"name": "Encrypted Drive", "type": "artifact", "quantity": 1},
        ],
        "weapons_dealer": [
            {"name": "Custom Pistol", "type": "weapon", "quantity": 1},
            {"name": "Weapons Cache Key", "type": "key", "quantity": 1},
        ],
        "driver": [
            {"name": "Safecar", "type": "vehicle", "quantity": 1},
            {"name": "Multiple IDs", "type": "document", "quantity": 1},
        ],
        "medic": [
            {"name": "Field Kit", "type": "artifact", "quantity": 1},
            {"name": "Favour Chip", "type": "token", "quantity": 1},
        ],
        "enforcer": [
            {"name": "Reinforced Knuckles", "type": "weapon", "quantity": 1},
            {"name": "Employer Letter", "type": "document", "quantity": 1},
        ],
    }
    return kits.get(archetype, [])
