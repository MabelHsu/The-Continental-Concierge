"""
Lore Tools — Retrieve world-building information and character data.

Uses both structured queries and semantic search via AlloyDB's hybrid
retrieval capabilities.

All functions use the async helpers from db.py — call with `await`.
"""

from typing import Optional

from app.tools.db import fetch_all, fetch_one


async def lookup_character(name: str) -> dict:
    """
    Get the full dossier for a character by name or alias.

    Args:
        name: Character name or alias (case-insensitive partial match)

    Returns:
        Character dossier including faction, location, traits, backstory,
        and recent events involving them.
    """
    row = await fetch_one(
        """
        SELECT id, name, alias, title, status, reputation, traits,
               backstory, notes, first_appeared_day, last_seen_day, last_seen_phase,
               faction_name, faction_type, location_name, location_type, district
        FROM v_character_dossier
        WHERE name ILIKE $1 OR alias ILIKE $1
        LIMIT 1
        """,
        f"%{name}%",
    )
    if not row:
        return {"error": f"No character found matching '{name}'"}
    return dict(row)


async def lookup_rule(query: str) -> dict:
    """
    Find a Continental hotel rule by number or keyword.

    Args:
        query: Rule number as a string (e.g., "1") or keyword (e.g., "weapons", "neutral ground")

    Returns:
        Matching rule with full text, penalty, and exceptions.
    """
    # Try to match by rule number first
    try:
        rule_num = int(query.strip())
        row = await fetch_one(
            "SELECT * FROM hotel_rules WHERE rule_number = $1 AND is_active = true",
            rule_num,
        )
    except ValueError:
        row = await fetch_one(
            """
            SELECT * FROM hotel_rules
            WHERE is_active = true
              AND (title ILIKE $1 OR description ILIKE $1 OR penalty ILIKE $1)
            ORDER BY rule_number
            LIMIT 1
            """,
            f"%{query}%",
        )
    if not row:
        return {"error": f"No rule found matching '{query}'"}
    return dict(row)


async def search_lore(query: str, category: Optional[str] = None, limit: int = 5) -> list[dict]:
    """
    Search world lore by keyword and optional category filter.

    Searches title, content, and tags. For semantic (vector) search, use the
    SQL search_lore() function directly via a raw DB query — this function
    provides keyword fallback that works without generating a query embedding.

    Args:
        query: Natural language search query
        category: Optional filter — one of: history, rule, tradition,
                  location_lore, character_lore, faction_lore, artifact,
                  ceremony, proverb, world_building
        limit: Max results (default 5)

    Returns:
        Ranked list of lore chunks with title, content, category, canon_level, tags.
    """
    if category:
        rows = await fetch_all(
            """
            SELECT id, title, content, category, canon_level, tags
            FROM lore_chunks
            WHERE category = $1
              AND (title ILIKE $2 OR content ILIKE $2)
            ORDER BY title
            LIMIT $3
            """,
            category,
            f"%{query}%",
            limit,
        )
    else:
        rows = await fetch_all(
            """
            SELECT id, title, content, category, canon_level, tags
            FROM lore_chunks
            WHERE title ILIKE $1 OR content ILIKE $1 OR $2 = ANY(tags)
            ORDER BY title
            LIMIT $3
            """,
            f"%{query}%",
            query.lower(),
            limit,
        )
    return [dict(r) for r in rows]


async def get_character_history(name: str, limit: int = 10) -> list[dict]:
    """
    Get the event history for a specific character — what they've been involved in.

    Args:
        name: Character name (partial match accepted)
        limit: Max events to return (default 10)

    Returns:
        Chronological list of events involving this character, newest first.
    """
    rows = await fetch_all(
        """
        SELECT e.day, e.phase, e.event_type, e.title, e.description,
               e.severity, e.is_resolved, ep.role,
               l.name AS location_name
        FROM events e
        JOIN event_participants ep ON e.id = ep.event_id
        JOIN characters c ON ep.character_id = c.id
        LEFT JOIN locations l ON e.location_id = l.id
        WHERE c.name ILIKE $1 OR c.alias ILIKE $1
        ORDER BY e.day DESC, e.phase
        LIMIT $2
        """,
        f"%{name}%",
        limit,
    )
    return [dict(r) for r in rows]


async def search_scenes(
    query: str, day_from: Optional[int] = None, day_to: Optional[int] = None
) -> list[dict]:
    """
    Search past scene memories by keyword and optional day range.

    Args:
        query: What you're looking for (keyword match against scene text)
        day_from: Start of day range (inclusive, optional)
        day_to: End of day range (inclusive, optional)

    Returns:
        Matching scene memories ordered by day descending, then significance.
    """
    rows = await fetch_all(
        """
        SELECT sm.id, sm.day, sm.phase, sm.scene_text, sm.mood,
               sm.significance, sm.tags, l.name AS location_name
        FROM scene_memories sm
        LEFT JOIN locations l ON sm.location_id = l.id
        WHERE sm.scene_text ILIKE $1
          AND ($2::int IS NULL OR sm.day >= $2)
          AND ($3::int IS NULL OR sm.day <= $3)
        ORDER BY sm.day DESC, sm.significance DESC
        LIMIT 10
        """,
        f"%{query}%",
        day_from,
        day_to,
    )
    return [dict(r) for r in rows]
