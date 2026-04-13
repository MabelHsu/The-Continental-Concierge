"""
Ledger Tools — Manage the social graph: debts, relationships, reputation.

The Ledger Agent is the only agent that should write to these tables.
Other agents may read through their own tools but should defer mutations here.

All functions use the async helpers from db.py — call with `await`.
"""

from typing import Optional

from app.tools.db import execute, fetch_all, fetch_one, transaction


async def get_debts(
    character_name: Optional[str] = None,
    status: str = "outstanding",
    marker_type: Optional[str] = None,
) -> list[dict]:
    """
    Query debts and markers. Returns outstanding obligations by default.

    Args:
        character_name: Filter by creditor or debtor name (optional, partial match)
        status: Filter by status — outstanding, called_in, fulfilled, betrayed,
                expired, transferred (default: outstanding)
        marker_type: Filter by type — blood_oath, marker, favor, debt, promise, threat

    Returns:
        List of debts with creditor/debtor names and details.
    """
    conditions = ["d.status = $1"]
    args: list = [status]

    if character_name:
        args.append(f"%{character_name}%")
        conditions.append(f"(cr.name ILIKE ${len(args)} OR db.name ILIKE ${len(args)})")
    if marker_type:
        args.append(marker_type)
        conditions.append(f"d.marker_type = ${len(args)}")

    where = "WHERE " + " AND ".join(conditions)
    rows = await fetch_all(
        f"""
        SELECT d.id, d.marker_type, d.description, d.value, d.status,
               d.created_day, d.called_in_day, d.notes,
               cr.name AS creditor_name, cr.alias AS creditor_alias,
               db.name AS debtor_name, db.alias AS debtor_alias,
               w.name AS witness_name
        FROM debts_markers d
        JOIN characters cr ON d.creditor_id = cr.id
        JOIN characters db ON d.debtor_id = db.id
        LEFT JOIN characters w ON d.witness_id = w.id
        {where}
        ORDER BY d.value DESC, d.created_day DESC
        """,
        *args,
    )
    return [dict(r) for r in rows]


async def create_debt(
    creditor_name: str,
    debtor_name: str,
    marker_type: str,
    description: str,
    value: int,
    witness_name: Optional[str] = None,
) -> dict:
    """
    Record a new debt or marker between two characters.

    Args:
        creditor_name: Who is owed (the one who gave the favour)
        debtor_name: Who owes (the one who received the favour)
        marker_type: blood_oath, marker, favor, debt, promise, or threat
        description: What the debt is for
        value: Severity/importance 1-10
        witness_name: Optional witness character name

    Returns:
        The created debt record, or an error dict if characters not found.
    """
    async with transaction() as conn:
        creditor = await conn.fetchrow(
            "SELECT id FROM characters WHERE name ILIKE $1", f"%{creditor_name}%"
        )
        debtor = await conn.fetchrow(
            "SELECT id FROM characters WHERE name ILIKE $1", f"%{debtor_name}%"
        )
        if not creditor:
            return {"error": f"Creditor '{creditor_name}' not found"}
        if not debtor:
            return {"error": f"Debtor '{debtor_name}' not found"}

        witness_id = None
        if witness_name:
            witness = await conn.fetchrow(
                "SELECT id FROM characters WHERE name ILIKE $1", f"%{witness_name}%"
            )
            witness_id = witness["id"] if witness else None

        current_day = await conn.fetchval(
            "SELECT current_day FROM story_state WHERE id = 1"
        )

        row = await conn.fetchrow(
            """
            INSERT INTO debts_markers
                (creditor_id, debtor_id, marker_type, description, value, witness_id, created_day)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            RETURNING id, marker_type, description, value, status
            """,
            creditor["id"],
            debtor["id"],
            marker_type,
            description,
            value,
            witness_id,
            current_day or 1,
        )
        return dict(row)


async def update_debt_status(
    debt_id: int,
    new_status: str,
    notes: Optional[str] = None,
) -> dict:
    """
    Update the status of a debt — called_in, fulfilled, betrayed, expired, transferred.

    Args:
        debt_id: The debt to update
        new_status: New status string
        notes: Explanation of what happened

    Returns:
        Updated debt record, or error if not found.
    """
    current = await fetch_one("SELECT current_day FROM story_state WHERE id = 1")
    day = current["current_day"] if current else 1

    # Build update based on which status transition this is
    if new_status == "called_in":
        row = await fetch_one(
            """
            UPDATE debts_markers SET status = $1, called_in_day = $2, updated_at = now()
            WHERE id = $3
            RETURNING id, marker_type, status, description
            """,
            new_status,
            day,
            debt_id,
        )
    elif new_status in ("fulfilled", "betrayed"):
        row = await fetch_one(
            """
            UPDATE debts_markers SET status = $1, fulfilled_day = $2, updated_at = now()
            WHERE id = $3
            RETURNING id, marker_type, status, description
            """,
            new_status,
            day,
            debt_id,
        )
    else:
        row = await fetch_one(
            """
            UPDATE debts_markers SET status = $1, updated_at = now()
            WHERE id = $2
            RETURNING id, marker_type, status, description
            """,
            new_status,
            debt_id,
        )

    if not row:
        return {"error": f"Debt {debt_id} not found"}

    if notes:
        await execute(
            "UPDATE debts_markers SET notes = $1 WHERE id = $2", notes, debt_id
        )

    return dict(row)


async def get_relationships(character_name: str) -> list[dict]:
    """
    Get all relationships for a character — allies, rivals, enemies, etc.

    Args:
        character_name: The character to look up (partial match accepted)

    Returns:
        List of relationships with other characters, ordered by strength.
    """
    rows = await fetch_all(
        """
        SELECT r.id, r.type, r.strength, r.public_known, r.origin_story, r.notes,
               a.name AS character_a, a.alias AS alias_a,
               b.name AS character_b, b.alias AS alias_b
        FROM relationships r
        JOIN characters a ON r.character_a_id = a.id
        JOIN characters b ON r.character_b_id = b.id
        WHERE a.name ILIKE $1 OR b.name ILIKE $1
        ORDER BY r.strength DESC
        """,
        f"%{character_name}%",
    )
    return [dict(r) for r in rows]


async def update_relationship(
    character_a: str,
    character_b: str,
    new_type: Optional[str] = None,
    strength_delta: Optional[int] = None,
    notes: Optional[str] = None,
) -> dict:
    """
    Update or create a relationship between two characters.

    Args:
        character_a: First character name
        character_b: Second character name
        new_type: New relationship type — ally, rival, mentor, protege, enemy,
                  neutral, business, romantic, family, grudging_respect (optional)
        strength_delta: Change in strength -100 to +100 (optional)
        notes: What caused the change (optional)

    Returns:
        Updated or created relationship record.
    """
    async with transaction() as conn:
        a = await conn.fetchrow(
            "SELECT id FROM characters WHERE name ILIKE $1", f"%{character_a}%"
        )
        b = await conn.fetchrow(
            "SELECT id FROM characters WHERE name ILIKE $1", f"%{character_b}%"
        )
        if not a:
            return {"error": f"Character '{character_a}' not found"}
        if not b:
            return {"error": f"Character '{character_b}' not found"}

        existing = await conn.fetchrow(
            """
            SELECT id, type, strength FROM relationships
            WHERE (character_a_id = $1 AND character_b_id = $2)
               OR (character_a_id = $2 AND character_b_id = $1)
            """,
            a["id"],
            b["id"],
        )

        if existing:
            updates = []
            args: list = []
            if new_type:
                args.append(new_type)
                updates.append(f"type = ${len(args)}")
            if strength_delta is not None:
                new_strength = max(0, min(100, existing["strength"] + strength_delta))
                args.append(new_strength)
                updates.append(f"strength = ${len(args)}")
            if notes:
                args.append(notes)
                updates.append(f"notes = ${len(args)}")

            if updates:
                args.append(existing["id"])
                row = await conn.fetchrow(
                    f"""
                    UPDATE relationships SET {', '.join(updates)}, updated_at = now()
                    WHERE id = ${len(args)}
                    RETURNING id, type, strength
                    """,
                    *args,
                )
                return dict(row)
            return dict(existing)

        # No existing relationship — create one
        row = await conn.fetchrow(
            """
            INSERT INTO relationships (character_a_id, character_b_id, type, strength, notes)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING id, type, strength
            """,
            a["id"],
            b["id"],
            new_type or "neutral",
            50,
            notes,
        )
        return dict(row)


async def get_reputation(character_name: str) -> dict:
    """
    Get a character's current reputation score and status.

    Args:
        character_name: Character to check (name or alias, partial match accepted)

    Returns:
        Reputation score, status, and faction. Error dict if not found.
    """
    row = await fetch_one(
        """
        SELECT name, alias, reputation, status, faction_name
        FROM v_character_dossier
        WHERE name ILIKE $1 OR alias ILIKE $1
        """,
        f"%{character_name}%",
    )
    if not row:
        return {"error": f"Character '{character_name}' not found"}
    return dict(row)


async def modify_reputation(
    character_name: str,
    delta: int,
    reason: str,
) -> dict:
    """
    Change a character's reputation score. Clamped to 0–100.

    Args:
        character_name: Who to modify (partial match accepted)
        delta: Change amount, positive or negative (e.g. +10, -20)
        reason: Why the change happened (stored in notes for the agent's context)

    Returns:
        New reputation score and any threshold effects (excommunicado risk, etc.).
    """
    row = await fetch_one(
        """
        UPDATE characters
        SET reputation = GREATEST(0, LEAST(100, reputation + $1)),
            updated_at = now()
        WHERE name ILIKE $2
        RETURNING name, reputation
        """,
        delta,
        f"%{character_name}%",
    )
    if not row:
        return {"error": f"Character '{character_name}' not found"}

    effects = []
    if row["reputation"] <= 0:
        effects.append("reputation at zero — excommunicado risk")
    elif row["reputation"] >= 90:
        effects.append("reputation exceptional — High Table attention possible")
    elif row["reputation"] <= 20:
        effects.append("reputation critically low — restricted access to Continental services")

    return {
        "name": row["name"],
        "reputation": row["reputation"],
        "change": delta,
        "reason": reason,
        "threshold_effects": effects,
    }


async def get_faction_standing() -> list[dict]:
    """
    Get current influence standings for all factions, ranked by influence.

    Returns:
        All factions ordered by influence descending.
    """
    rows = await fetch_all(
        """
        SELECT name, type, influence, status, territory, description
        FROM factions
        ORDER BY influence DESC
        """
    )
    return [dict(r) for r in rows]
