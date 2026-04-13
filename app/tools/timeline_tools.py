"""
Timeline Tools — Spatial and temporal tracking.

Manages character locations, event logging, and collision detection.
"Collision" = two hostile characters in the same Continental location,
or an expired mission deadline that hasn't been resolved.

All functions use the async helpers from db.py — call with `await`.
"""

from typing import Optional

from app.tools.db import execute, fetch_all, fetch_one, transaction


async def get_current_locations() -> list[dict]:
    """
    Get a map of all locations and who is currently there.

    Returns:
        List of locations with characters_present arrays. Uses v_current_scene view
        which aggregates active characters per location.
    """
    rows = await fetch_all(
        "SELECT * FROM v_current_scene ORDER BY location_name"
    )
    return [dict(r) for r in rows]


async def move_character(
    character_name: str,
    destination: str,
    reason: Optional[str] = None,
) -> dict:
    """
    Move a character to a new location and check for hostile collisions.

    Args:
        character_name: Who to move (partial match accepted)
        destination: Location name to move to (partial match accepted)
        reason: Why they're moving (optional, for narrative context)

    Returns:
        dict with character name, new location, and any hostile collisions detected.
        Error dict if character or location not found, or location is inaccessible.
    """
    async with transaction() as conn:
        char = await conn.fetchrow(
            "SELECT id, name, current_location_id FROM characters WHERE name ILIKE $1",
            f"%{character_name}%",
        )
        if not char:
            return {"error": f"Character '{character_name}' not found"}

        loc = await conn.fetchrow(
            "SELECT id, name, current_status, is_continental FROM locations WHERE name ILIKE $1",
            f"%{destination}%",
        )
        if not loc:
            return {"error": f"Location '{destination}' not found"}
        if loc["current_status"] in ("destroyed", "compromised"):
            return {"error": f"Location '{loc['name']}' is {loc['current_status']} — access denied"}

        # Detect hostile characters already at the destination
        hostile = await conn.fetch(
            """
            SELECT c.name
            FROM characters c
            JOIN relationships r
                ON (r.character_a_id = $1 AND r.character_b_id = c.id)
                OR (r.character_b_id = $1 AND r.character_a_id = c.id)
            WHERE c.current_location_id = $2
              AND r.type = 'enemy'
              AND c.status = 'active'
            """,
            char["id"],
            loc["id"],
        )

        await conn.execute(
            """
            UPDATE characters
            SET current_location_id = $1, updated_at = now()
            WHERE id = $2
            """,
            loc["id"],
            char["id"],
        )

        return {
            "character": char["name"],
            "new_location": loc["name"],
            "reason": reason,
            "is_continental": loc["is_continental"],
            "hostile_collisions": [r["name"] for r in hostile],
        }


async def log_event(
    event_type: str,
    title: str,
    description: str,
    location: Optional[str] = None,
    severity: int = 3,
    participants: Optional[list[dict]] = None,
    is_public: bool = True,
) -> dict:
    """
    Record a new event in the world timeline.

    Args:
        event_type: One of — arrival, departure, meeting, conflict, transaction,
                    ceremony, violation, request, favor, assassination, negotiation,
                    betrayal, alliance, discovery, custom
        title: Short descriptive title (shown in timeline views)
        description: Full narrative description of what happened
        location: Location name where it occurred (optional, partial match)
        severity: 1–10 scale of how significant the event is (default 3)
        participants: List of dicts with 'name' and 'role' keys.
                      Roles: instigator, participant, witness, victim, beneficiary, target
        is_public: Whether other characters in the hotel would hear about it (default True)

    Returns:
        The created event with id, day, phase, and title.
    """
    async with transaction() as conn:
        current = await conn.fetchrow(
            "SELECT current_day, current_phase FROM story_state WHERE id = 1"
        )
        day = current["current_day"] if current else 1
        phase = current["current_phase"] if current else "evening"

        loc_id = None
        if location:
            loc = await conn.fetchrow(
                "SELECT id FROM locations WHERE name ILIKE $1", f"%{location}%"
            )
            loc_id = loc["id"] if loc else None

        event = await conn.fetchrow(
            """
            INSERT INTO events
                (day, phase, event_type, title, description, location_id, severity, is_public)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            RETURNING id, day, phase, event_type, title
            """,
            day,
            phase,
            event_type,
            title,
            description,
            loc_id,
            severity,
            is_public,
        )

        if participants:
            for p in participants:
                char = await conn.fetchrow(
                    "SELECT id FROM characters WHERE name ILIKE $1",
                    f"%{p.get('name', '')}%",
                )
                if char:
                    role = p.get("role", "participant")
                    await conn.execute(
                        """
                        INSERT INTO event_participants (event_id, character_id, role)
                        VALUES ($1, $2, $3)
                        ON CONFLICT DO NOTHING
                        """,
                        event["id"],
                        char["id"],
                        role,
                    )

        return dict(event)


async def get_timeline(
    day_from: Optional[int] = None,
    day_to: Optional[int] = None,
    location: Optional[str] = None,
    limit: int = 20,
) -> list[dict]:
    """
    Get events from the world timeline with optional filters.

    Args:
        day_from: Start of day range inclusive (optional)
        day_to: End of day range inclusive (optional)
        location: Filter by location name (optional, partial match)
        limit: Max results (default 20)

    Returns:
        Events ordered by day descending, then phase descending.
    """
    conditions: list[str] = []
    args: list = []

    if day_from is not None:
        args.append(day_from)
        conditions.append(f"e.day >= ${len(args)}")
    if day_to is not None:
        args.append(day_to)
        conditions.append(f"e.day <= ${len(args)}")
    if location:
        args.append(f"%{location}%")
        conditions.append(f"l.name ILIKE ${len(args)}")

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    args.append(limit)

    rows = await fetch_all(
        f"""
        SELECT e.id, e.day, e.phase, e.event_type, e.title, e.description,
               e.severity, e.is_public, e.is_resolved,
               l.name AS location_name
        FROM events e
        LEFT JOIN locations l ON e.location_id = l.id
        {where}
        ORDER BY e.day DESC,
            CASE e.phase WHEN 'dawn' THEN 1 WHEN 'morning' THEN 2
                         WHEN 'afternoon' THEN 3 WHEN 'evening' THEN 4
                         WHEN 'night' THEN 5 END DESC
        LIMIT ${len(args)}
        """,
        *args,
    )
    return [dict(r) for r in rows]


async def detect_collisions() -> list[dict]:
    """
    Scan for timeline and spatial conflicts that need resolution.

    Checks for:
    - Hostile characters in the same Continental location (rule violation risk)
    - Pending rule violations awaiting adjudication

    Returns:
        List of collision objects, each with 'type', 'severity', and details.
    """
    collisions: list[dict] = []

    # 1. Enemy characters in the same Continental location
    hostile_rows = await fetch_all(
        """
        SELECT l.name AS location, a.name AS character_a, b.name AS character_b
        FROM relationships r
        JOIN characters a ON r.character_a_id = a.id
        JOIN characters b ON r.character_b_id = b.id
        JOIN locations l ON a.current_location_id = l.id
        WHERE r.type = 'enemy'
          AND a.current_location_id = b.current_location_id
          AND a.current_location_id IS NOT NULL
          AND l.is_continental = true
          AND a.status = 'active'
          AND b.status = 'active'
        """
    )
    for row in hostile_rows:
        collisions.append(
            {"type": "hostile_collision", "severity": 8, **dict(row)}
        )

    # 2. Rule violations pending adjudication
    violation_rows = await fetch_all(
        """
        SELECT rv.id, c.name AS violator, hr.title AS rule, rv.severity
        FROM rule_violations rv
        JOIN characters c ON rv.violator_id = c.id
        JOIN hotel_rules hr ON rv.rule_id = hr.id
        WHERE rv.adjudication = 'pending'
        """
    )
    for row in violation_rows:
        collisions.append(
            {"type": "pending_violation", **dict(row)}
        )

    return collisions


async def get_upcoming_deadlines(within_phases: int = 3) -> list[dict]:
    """
    Get missions with deadlines approaching within N phases of the current time.

    Args:
        within_phases: How many phases ahead to look (default 3, roughly half a day)

    Returns:
        Missions ordered by deadline day then priority.
    """
    current = await fetch_one(
        "SELECT current_day FROM story_state WHERE id = 1"
    )
    day = current["current_day"] if current else 1
    # Rough conversion: 5 phases per day
    lookahead_days = (within_phases // 5) + 1

    rows = await fetch_all(
        """
        SELECT m.id, m.title, m.deadline_day, m.deadline_phase,
               m.priority, m.description, m.status,
               req.name AS requested_by
        FROM missions m
        LEFT JOIN characters req ON m.requested_by_id = req.id
        WHERE m.status IN ('pending', 'active')
          AND m.deadline_day IS NOT NULL
          AND m.deadline_day <= $1
        ORDER BY m.deadline_day, m.priority DESC
        """,
        day + lookahead_days,
    )
    return [dict(r) for r in rows]


async def check_character_availability(character_name: str) -> dict:
    """
    Check if a character is available for interaction or has conflicting obligations.

    Args:
        character_name: The character to check (name or alias, partial match)

    Returns:
        dict with availability status, current location, and active mission count.
        available=True means status is 'active' and no active missions assigned.
    """
    row = await fetch_one(
        """
        SELECT c.name, c.status, c.alias,
               l.name AS current_location,
               (
                   SELECT COUNT(*)
                   FROM missions m
                   WHERE m.assigned_to_id = c.id AND m.status = 'active'
               ) AS active_missions
        FROM characters c
        LEFT JOIN locations l ON c.current_location_id = l.id
        WHERE c.name ILIKE $1 OR c.alias ILIKE $1
        """,
        f"%{character_name}%",
    )
    if not row:
        return {"error": f"Character '{character_name}' not found"}

    available = row["status"] == "active" and row["active_missions"] == 0
    return {**dict(row), "available": available}
