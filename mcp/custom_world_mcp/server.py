"""
Custom World MCP Server
========================
MCP server for write operations that are too complex for
the Toolbox's SQL-only approach. Handles state mutations,
multi-step transactions, and business logic.

Deploy as a Cloud Run service.
"""

import json
import os
from contextlib import asynccontextmanager

import asyncpg
from mcp.server import Server
from mcp.server.fastmcp import FastMCP
from mcp.types import Tool, TextContent

# ── Server Setup ──────────────────────────────────────────────

mcp = FastMCP(
    name="continental-world",
    version="1.0.0",
)

# Database pool
_pool = None


async def get_pool():
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            host=os.environ.get("ALLOYDB_HOST", "localhost"),
            port=int(os.environ.get("ALLOYDB_PORT", "5432")),
            database=os.environ.get("ALLOYDB_DATABASE", "continental"),
            user=os.environ.get("ALLOYDB_USER", "continental_app"),
            password=os.environ.get("ALLOYDB_PASSWORD", ""),
            min_size=2,
            max_size=10,
        )
    return _pool


# ── Write Tools ───────────────────────────────────────────────

@mcp.tool()
async def create_event(
    title: str,
    description: str,
    story_day: int,
    story_time: str,
    location_name: str,
    event_type: str,
    participant_names: list[str],
    is_public: bool = True,
    turn_number: int = 0,
) -> str:
    """
    Schedule a new event in the world timeline.
    Resolves location and participant names to IDs.
    Returns the event data plus any detected conflicts.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            # Resolve location
            loc = await conn.fetchrow(
                "SELECT id, name, is_consecrated FROM locations WHERE LOWER(name) LIKE LOWER($1)",
                f"%{location_name}%",
            )
            if not loc:
                return json.dumps({"error": f"Location '{location_name}' not found"})

            # Resolve participants
            participant_ids = []
            for name in participant_names:
                char = await conn.fetchrow(
                    "SELECT id FROM characters WHERE LOWER(name) = LOWER($1)", name
                )
                if char:
                    participant_ids.append(char["id"])
                else:
                    return json.dumps({"error": f"Character '{name}' not found"})

            # Check consecrated ground
            warnings = []
            if loc["is_consecrated"] and event_type in (
                "conflict", "assassination", "negotiation", "transaction"
            ):
                warnings.append(f"Rule 1 violation: {event_type} at consecrated {loc['name']}")

            # Insert event
            row = await conn.fetchrow(
                """
                INSERT INTO events (story_day, story_time, title, description,
                    location_id, event_type, participants, is_public, turn_number)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                RETURNING id
                """,
                story_day, story_time, title, description,
                loc["id"], event_type, participant_ids, is_public, turn_number,
            )

            return json.dumps({
                "event_id": str(row["id"]),
                "title": title,
                "location": loc["name"],
                "warnings": warnings,
            })


@mcp.tool()
async def create_debt(
    creditor_name: str,
    debtor_name: str,
    marker_type: str,
    description: str,
    value_weight: int,
) -> str:
    """Create a new debt/marker between two characters."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        cr = await conn.fetchrow(
            "SELECT id FROM characters WHERE LOWER(name) = LOWER($1)", creditor_name
        )
        db = await conn.fetchrow(
            "SELECT id FROM characters WHERE LOWER(name) = LOWER($1)", debtor_name
        )
        if not cr or not db:
            return json.dumps({"error": "Character not found"})

        row = await conn.fetchrow(
            """
            INSERT INTO debts_markers (creditor_id, debtor_id, marker_type,
                description, value_weight)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING id, status
            """,
            cr["id"], db["id"], marker_type, description, value_weight,
        )

        return json.dumps({
            "debt_id": str(row["id"]),
            "creditor": creditor_name,
            "debtor": debtor_name,
            "type": marker_type,
            "weight": value_weight,
        })


@mcp.tool()
async def resolve_debt(debt_id: str, resolution: str, reason: str) -> str:
    """
    Resolve an outstanding debt.
    resolution: fulfilled | forgiven | disputed
    Blood oaths can only be fulfilled.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            debt = await conn.fetchrow(
                "SELECT * FROM debts_markers WHERE id = $1::uuid", debt_id
            )
            if not debt:
                return json.dumps({"error": "Debt not found"})

            if debt["marker_type"] == "blood_oath" and resolution != "fulfilled":
                return json.dumps({
                    "error": "Blood oaths can only be fulfilled. Anything else is a capital offense."
                })

            await conn.execute(
                "UPDATE debts_markers SET status = $1, resolved_at = now() WHERE id = $2::uuid",
                resolution, debt_id,
            )

            return json.dumps({
                "debt_id": debt_id,
                "resolution": resolution,
                "reason": reason,
            })


@mcp.tool()
async def move_character(character_name: str, location_name: str) -> str:
    """Move a character to a new location."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        char = await conn.fetchrow(
            """
            SELECT c.id, c.name, l.name AS old_location, l.city AS old_city
            FROM characters c LEFT JOIN locations l ON c.current_location_id = l.id
            WHERE LOWER(c.name) = LOWER($1)
            """,
            character_name,
        )
        if not char:
            return json.dumps({"error": f"Character '{character_name}' not found"})

        loc = await conn.fetchrow(
            "SELECT id, name, city FROM locations WHERE LOWER(name) LIKE LOWER($1)",
            f"%{location_name}%",
        )
        if not loc:
            return json.dumps({"error": f"Location '{location_name}' not found"})

        await conn.execute(
            "UPDATE characters SET current_location_id = $1, updated_at = now() WHERE id = $2",
            loc["id"], char["id"],
        )

        cross_city = char["old_city"] and loc["city"] and char["old_city"] != loc["city"]

        return json.dumps({
            "character": character_name,
            "from": char["old_location"],
            "to": loc["name"],
            "cross_city_travel": cross_city,
        })


@mcp.tool()
async def update_reputation(character_name: str, change: int, reason: str) -> str:
    """Adjust a character's reputation score. Bounded 0-100."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        char = await conn.fetchrow(
            "SELECT id, reputation FROM characters WHERE LOWER(name) = LOWER($1)",
            character_name,
        )
        if not char:
            return json.dumps({"error": f"Character '{character_name}' not found"})

        new_rep = max(0, min(100, char["reputation"] + change))
        await conn.execute(
            "UPDATE characters SET reputation = $1, updated_at = now() WHERE id = $2",
            new_rep, char["id"],
        )

        return json.dumps({
            "character": character_name,
            "old_reputation": char["reputation"],
            "change": change,
            "new_reputation": new_rep,
            "reason": reason,
        })


@mcp.tool()
async def record_rule_violation(
    rule_number: int,
    violator_name: str,
    description: str,
) -> str:
    """Record a hotel rule violation. Sets adjudication to pending."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rule = await conn.fetchrow(
            "SELECT id, title, severity FROM hotel_rules WHERE rule_number = $1",
            rule_number,
        )
        violator = await conn.fetchrow(
            "SELECT id FROM characters WHERE LOWER(name) = LOWER($1)", violator_name
        )

        if not rule or not violator:
            return json.dumps({"error": "Rule or character not found"})

        row = await conn.fetchrow(
            """
            INSERT INTO rule_violations (rule_id, violator_id, description, adjudication)
            VALUES ($1, $2, $3, 'pending')
            RETURNING id
            """,
            rule["id"], violator["id"], description,
        )

        return json.dumps({
            "violation_id": str(row["id"]),
            "rule": rule["title"],
            "severity": rule["severity"],
            "violator": violator_name,
        })


@mcp.tool()
async def save_story_snapshot(
    turn_number: int,
    story_day: int,
    summary: str,
) -> str:
    """Save a world state snapshot for rollback/retrieval."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        chars = await conn.fetch(
            "SELECT id, name, status, reputation, current_location_id FROM characters"
        )
        debts = await conn.fetch(
            "SELECT id, creditor_id, debtor_id, marker_type, status FROM debts_markers"
        )

        world_state = {
            "characters": [dict(c) for c in chars],
            "debts": [dict(d) for d in debts],
        }

        row = await conn.fetchrow(
            """
            INSERT INTO story_snapshots (turn_number, story_day, summary, world_state)
            VALUES ($1, $2, $3, $4::jsonb)
            RETURNING id
            """,
            turn_number, story_day, summary, json.dumps(world_state, default=str),
        )

        return json.dumps({"snapshot_id": str(row["id"]), "turn": turn_number})


# ── Entry Point ───────────────────────────────────────────────

if __name__ == "__main__":
    mcp.run(transport="sse")
