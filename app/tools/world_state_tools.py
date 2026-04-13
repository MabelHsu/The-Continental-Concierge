"""
World State Tools — Read and mutate the core world state.

story_state is a singleton table (always id=1) that holds the world clock:
current day, current phase, crisis level, and hotel status. Everything in the
world is anchored to this clock.

All functions use the async helpers from db.py — call with `await`.
"""

import json
from typing import Optional

from app.tools.db import execute, fetch_all, fetch_one


# Phase order for advance_time calculations
_PHASES = ["morning", "afternoon", "evening", "night", "dawn"]


async def get_world_state() -> dict:
    """
    Get the current state of the world: day, phase, crisis level, hotel status.

    Returns:
        dict with keys: current_day, current_phase, crisis_level, crisis_name,
        hotel_status, high_table_edict, active_character_count, pending_mission_count.
        Returns an error dict if story_state has not been initialised.
    """
    row = await fetch_one(
        """
        SELECT
            s.current_day, s.current_phase, s.crisis_level, s.crisis_name,
            s.hotel_status, s.high_table_edict, s.updated_at,
            (SELECT COUNT(*) FROM characters WHERE status = 'active')
                AS active_character_count,
            (SELECT COUNT(*) FROM missions WHERE status IN ('pending', 'active'))
                AS pending_mission_count
        FROM story_state s
        WHERE s.id = 1
        """
    )
    if not row:
        return {"error": "World state not initialised — run db/seed_lore.sql first"}
    return dict(row)


async def advance_time(phases_to_advance: int = 1) -> dict:
    """
    Advance the world clock by N phases. Day increments when dawn rolls over to morning.

    Args:
        phases_to_advance: Number of phases to advance (default 1).
                           Phases cycle: morning → afternoon → evening → night → dawn → morning…

    Returns:
        dict with new day, new phase, and how many full days were advanced.
    """
    current = await fetch_one(
        "SELECT current_day, current_phase FROM story_state WHERE id = 1"
    )
    if not current:
        return {"error": "World state not initialised"}

    phase_idx = _PHASES.index(current["current_phase"])
    new_idx = (phase_idx + phases_to_advance) % len(_PHASES)
    days_advanced = (phase_idx + phases_to_advance) // len(_PHASES)
    new_day = current["current_day"] + days_advanced
    new_phase = _PHASES[new_idx]

    await execute(
        """
        UPDATE story_state
        SET current_day = $1, current_phase = $2, updated_at = now()
        WHERE id = 1
        """,
        new_day,
        new_phase,
    )

    return {
        "day": new_day,
        "phase": new_phase,
        "days_advanced": days_advanced,
        "phases_advanced": phases_to_advance,
    }


async def get_events(
    day: Optional[int] = None,
    phase: Optional[str] = None,
    character_name: Optional[str] = None,
    event_type: Optional[str] = None,
    limit: int = 10,
) -> list[dict]:
    """
    Query the event log with optional filters. Returns recent events by default.

    Args:
        day: Filter by story day (optional)
        phase: Filter by phase — morning, afternoon, evening, night, dawn (optional)
        character_name: Filter by participant name (optional, partial match)
        event_type: Filter by event type — arrival, conflict, violation, etc. (optional)
        limit: Max results (default 10)

    Returns:
        List of events with participants, newest first.
    """
    conditions: list[str] = []
    args: list = []

    if day is not None:
        args.append(day)
        conditions.append(f"e.day = ${len(args)}")
    if phase is not None:
        args.append(phase)
        conditions.append(f"e.phase = ${len(args)}")
    if event_type is not None:
        args.append(event_type)
        conditions.append(f"e.event_type = ${len(args)}")
    if character_name is not None:
        args.append(f"%{character_name}%")
        conditions.append(
            f"""EXISTS (
                SELECT 1 FROM event_participants ep2
                JOIN characters c2 ON ep2.character_id = c2.id
                WHERE ep2.event_id = e.id
                  AND (c2.name ILIKE ${len(args)} OR c2.alias ILIKE ${len(args)})
            )"""
        )

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    args.append(limit)

    rows = await fetch_all(
        f"""
        SELECT e.id, e.day, e.phase, e.event_type, e.title, e.description,
               e.severity, e.is_public, e.is_resolved, e.resolution,
               l.name AS location_name,
               json_agg(json_build_object('name', c.name, 'role', ep.role))
                 FILTER (WHERE c.id IS NOT NULL) AS participants
        FROM events e
        LEFT JOIN locations l ON e.location_id = l.id
        LEFT JOIN event_participants ep ON e.id = ep.event_id
        LEFT JOIN characters c ON ep.character_id = c.id
        {where}
        GROUP BY e.id, e.day, e.phase, e.event_type, e.title, e.description,
                 e.severity, e.is_public, e.is_resolved, e.resolution, l.name
        ORDER BY e.day DESC,
            CASE e.phase WHEN 'dawn' THEN 1 WHEN 'morning' THEN 2
                         WHEN 'afternoon' THEN 3 WHEN 'evening' THEN 4
                         WHEN 'night' THEN 5 END DESC
        LIMIT ${len(args)}
        """,
        *args,
    )
    return [dict(r) for r in rows]


async def create_story_snapshot(summary: str, active_threads: list[str]) -> dict:
    """
    Save a snapshot of the current narrative state. Called at the end of each phase.

    Args:
        summary: Text summary of what has happened and what tensions are active
        active_threads: List of ongoing storylines (e.g. ["Winston's debt to Sofia",
                        "The Casablanca assassination contract"])

    Returns:
        The created snapshot with id, day, and phase.
    """
    current = await fetch_one(
        "SELECT current_day, current_phase, crisis_level FROM story_state WHERE id = 1"
    )
    if not current:
        return {"error": "World state not initialised"}

    row = await fetch_one(
        """
        INSERT INTO story_snapshots
            (day, phase, summary, active_threads, tension_level, key_changes)
        VALUES ($1, $2, $3, $4, $5, '[]')
        RETURNING id, day, phase, summary
        """,
        current["current_day"],
        current["current_phase"],
        summary,
        json.dumps(active_threads),
        current["crisis_level"],
    )
    return dict(row) if row else {"error": "Snapshot insert failed"}
