"""
Player Tools — All read/write operations for the player character layer.

These tools are used by:
  - The Onboarding Agent  (creates the player row)
  - The Concierge Orchestrator  (reads player state for routing context)
  - The Ledger Agent  (reads/writes player debts and reputation)
  - The Timeline Agent  (reads/writes player location)
  - The server  (REST endpoints for /player)

Design rule: these tools are the only place that touches player_characters,
player_inventory, player_faction_standing, and player_mission_log tables.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

from app.tools.db import execute, fetch_all, fetch_one, fetch_val, transaction

logger = logging.getLogger(__name__)


# ── Player State ───────────────────────────────────────────────────────────────


async def get_player(session_id: str) -> Optional[dict]:
    """
    Get the full player state for a session. Returns None if not yet created.

    Uses the player_status_view for a fully joined, flat representation
    including faction name, location name, active mission details, and
    inventory/faction standing summaries.

    Args:
        session_id: The session identifier from the server.

    Returns:
        Player status dict, or None if this session has no player character yet.
    """
    return await fetch_one(
        "SELECT * FROM player_status_view WHERE session_id = $1",
        session_id,
    )


async def create_player_character(
    session_id: str,
    user_id: str,
    creation_path: str,
) -> dict:
    """
    Create a new player character row at the start of a session.

    Called at the very beginning of onboarding, before the player has
    answered any questions. Sets creation_path and leaves identity fields
    NULL — those are filled in by advance_onboarding_step().

    Args:
        session_id: From the server session.
        user_id: From ChatRequest.user_id.
        creation_path: 'mystery' or 'custom'.

    Returns:
        The newly created player_characters row.
    """
    row = await fetch_one(
        """
        INSERT INTO player_characters (session_id, user_id, creation_path)
        VALUES ($1, $2, $3)
        ON CONFLICT (session_id) DO UPDATE
            SET user_id = EXCLUDED.user_id,
                creation_path = EXCLUDED.creation_path
        RETURNING *
        """,
        session_id,
        user_id,
        creation_path,
    )
    logger.info("Player character created: session=%s path=%s", session_id, creation_path)
    return row


async def advance_onboarding_step(
    session_id: str,
    step: int,
    charon_line: str,
    player_response: str,
    alias: str | None = None,
    name: str | None = None,
    archetype: str | None = None,
    faction_id: int | None = None,
    identity_clue: str | None = None,
    identity_revealed: bool = False,
) -> dict:
    """
    Record a single onboarding exchange and update the player_characters row.

    The onboarding agent calls this after each Charon/player turn.
    Pass only the fields you confidently extracted from the player's response.
    All extracted fields are optional — omit anything you are not certain about.

    Args:
        session_id: The current session.
        step: Onboarding step number (1-based).
        charon_line: The exact line Charon just spoke.
        player_response: The player's reply.
        alias: Working name/handle the player provided (e.g. "Ghost", "Pamonha Lady").
        name: Full name if explicitly stated — leave null if uncertain.
        archetype: One of: assassin, cleaner, fixer, information_broker,
                   weapons_dealer, driver, medic, enforcer.
        faction_id: Integer ID of the player's faction, or null for independent.
        identity_clue: One-sentence inference about identity/history/connections.
        identity_revealed: Set true only on the final mystery-path revelation step.

    Returns:
        Updated player_characters row.
    """
    # 1. Log the exchange
    player = await fetch_one("SELECT id, alias FROM player_characters WHERE session_id = $1", session_id)
    if not player:
        raise ValueError(f"No player character for session {session_id}")

    player_id = player["id"]
    existing_alias = player["alias"]

    # Reconstruct extracted_data dict for the audit log
    extracted_data_log: dict[str, Any] = {}
    if alias:
        extracted_data_log["alias"] = alias
    if name:
        extracted_data_log["name"] = name
    if archetype:
        extracted_data_log["archetype"] = archetype
    if faction_id is not None:
        extracted_data_log["faction_id"] = faction_id
    if identity_clue:
        extracted_data_log["identity_clue"] = identity_clue
    if identity_revealed:
        extracted_data_log["identity_revealed"] = identity_revealed

    await execute(
        """
        INSERT INTO onboarding_exchanges
            (player_id, step, charon_line, player_response, extracted_data)
        VALUES ($1, $2, $3, $4, $5)
        """,
        player_id,
        step,
        charon_line,
        player_response,
        json.dumps(extracted_data_log),
    )

    # 2. Build updates — alias is always preferred over model-generated name
    updates: dict[str, Any] = {"onboarding_step": step}

    if alias:
        updates["alias"] = alias
        # Mirror alias → name so both fields are populated
        updates["name"] = alias
    elif name:
        # Only set name if no alias exists yet; never overwrite a player-provided alias
        if not existing_alias:
            updates["name"] = name
        else:
            # Alias already set — keep it canonical, ignore model-invented name
            updates["name"] = existing_alias

    if archetype:
        updates["archetype"] = archetype
    if faction_id is not None:
        updates["faction_id"] = faction_id
    if identity_revealed:
        updates["identity_revealed"] = True

    # Append identity clue atomically (separate UPDATE to avoid SET clause complexity)
    if identity_clue:
        await execute(
            """
            UPDATE player_characters
            SET identity_clues = identity_clues || $1::jsonb
            WHERE session_id = $2
            """,
            json.dumps([identity_clue]),
            session_id,
        )

    # 3. Build SET clause dynamically (safe — keys are allowlisted above)
    set_clauses = ", ".join(f"{k} = ${i + 2}" for i, k in enumerate(updates.keys()))
    values = list(updates.values())
    await execute(
        f"UPDATE player_characters SET {set_clauses} WHERE session_id = $1",
        session_id,
        *values,
    )

    return await fetch_one("SELECT * FROM player_characters WHERE session_id = $1", session_id)


async def complete_onboarding(session_id: str) -> dict:
    """
    Mark onboarding as complete and create the mirroring characters row.

    After this call the player is a full participant in the world: the
    Archivist can look them up by name, the Ledger tracks their debts,
    and the Timeline places them on the map.

    Args:
        session_id: The session.

    Returns:
        The finalised player_status_view row.
    """
    player = await fetch_one("SELECT * FROM player_characters WHERE session_id = $1", session_id)
    if not player:
        raise ValueError(f"No player for session {session_id}")

    # Idempotency guard — if already complete, return current state without re-running.
    # This prevents the onboarding agent from looping and calling this multiple times.
    if player["onboarding_complete"]:
        return dict(player)

    async with transaction() as conn:
        # Create / upsert a row in the shared characters table
        # Prefer alias over name: the alias is what the player explicitly said
        # in their own words. 'name' can be set by the model at the revelation
        # step and occasionally gets fabricated — alias is always player-provided.
        canonical_name = player["alias"] or player["name"] or "Unknown"

        char_id = await conn.fetchval(
            """
            INSERT INTO characters
                (name, alias, title, faction_id, status, reputation,
                 traits, backstory, current_location_id, first_appeared_day)
            VALUES
                ($1, $2, $3, $4, 'active', $5,
                 $6, $7, $8, 1)
            ON CONFLICT (name) DO UPDATE
                SET alias = EXCLUDED.alias,
                    updated_at = now()
            RETURNING id
            """,
            canonical_name,
            player["alias"],
            player["title"],
            player["faction_id"],
            player["reputation"],
            json.dumps(["player"]),  # tag as player character in traits
            player["backstory"],
            player["current_location_id"],
        )

        # Link back and mark complete
        await conn.execute(
            """
            UPDATE player_characters
            SET onboarding_complete = true,
                identity_revealed   = true,
                character_id        = $2
            WHERE session_id = $1
            """,
            session_id,
            char_id,
        )

        # Grant starting inventory based on archetype
        if player["archetype"]:
            starting_items = _starting_inventory(player["archetype"])
            if starting_items:
                await conn.executemany(
                    """
                    INSERT INTO player_inventory
                        (player_id, item_type, name, description, quantity, acquired_day)
                    VALUES ($1, $2, $3, $4, $5, 1)
                    """,
                    [(player["id"], *item) for item in starting_items],
                )

        # Seed faction standings
        await conn.execute(
            """
            INSERT INTO player_faction_standing (player_id, faction_id, standing)
            SELECT $1, id, 50 FROM factions
            ON CONFLICT DO NOTHING
            """,
            player["id"],
        )
        # Adjust home faction standing
        if player["faction_id"]:
            await conn.execute(
                """
                UPDATE player_faction_standing
                SET standing = 70
                WHERE player_id = $1 AND faction_id = $2
                """,
                player["id"],
                player["faction_id"],
            )

    logger.info("Onboarding complete: session=%s character_id=%d", session_id, char_id)
    return await fetch_one("SELECT * FROM player_status_view WHERE session_id = $1", session_id)


def _starting_inventory(archetype: str) -> list[tuple]:
    """Return (item_type, name, description, quantity) tuples for archetype."""
    items = {
        "assassin": [
            ("weapon", "Suppressed Pistol", "Standard issue. Clean.", 1),
            ("document", "Clean Passport", "One of three.", 1),
        ],
        "cleaner": [
            ("artifact", "Burner Phone", "Pre-loaded, untraceable.", 1),
            ("token", "Continental Coin", "Seven gold coins.", 7),
        ],
        "fixer": [
            ("intel", "Contact List", "Encrypted. Three tier-one names.", 1),
            ("document", "Blank Marker", "Unsigned. Waiting for blood.", 1),
        ],
        "information_broker": [
            ("intel", "Dossier Fragment", "Partial file. Someone important.", 1),
            ("artifact", "Encrypted Drive", "8TB. The price is steep.", 1),
        ],
        "weapons_dealer": [
            ("weapon", "Custom Pistol", "Engraved. Personal use only.", 1),
            ("artifact", "Weapons Cache Key", "Location known only to you.", 1),
        ],
        "driver": [
            ("vehicle", "Safecar", "Reinforced. Clean plates.", 1),
            ("document", "Multiple IDs", "Six identities, three cities.", 1),
        ],
        "medic": [
            ("artifact", "Field Kit", "Military grade. No questions asked.", 1),
            ("token", "Favour Chip", "One debt outstanding. Mutual.", 1),
        ],
        "enforcer": [
            ("weapon", "Reinforced Knuckles", "Subtle.", 1),
            ("document", "Employer Letter", "Authorised use of force.", 1),
        ],
    }
    return items.get(archetype, [])


# ── Player Stat Mutations ──────────────────────────────────────────────────────


async def update_player_reputation(
    session_id: str,
    delta: int,
    reason: str,
) -> dict:
    """
    Adjust the player's reputation score.

    Also updates the mirroring characters row if character_id is set.

    Args:
        session_id: The session.
        delta: Change amount (negative to decrease).
        reason: Narrative reason for the change (logged to events).

    Returns:
        dict with new_reputation, old_reputation, delta, and any threshold effects.
    """
    player = await fetch_one(
        "SELECT id, reputation, character_id FROM player_characters WHERE session_id = $1",
        session_id,
    )
    if not player:
        raise ValueError(f"No player for session {session_id}")

    old_rep = player["reputation"]
    new_rep = max(0, min(100, old_rep + delta))

    await execute(
        "UPDATE player_characters SET reputation = $1 WHERE session_id = $2",
        new_rep,
        session_id,
    )

    # Mirror to characters table
    if player["character_id"]:
        await execute(
            "UPDATE characters SET reputation = $1 WHERE id = $2",
            new_rep,
            player["character_id"],
        )

    # Threshold effects
    effects = []
    if old_rep > 20 >= new_rep:
        effects.append("WARNING: Reputation approaching excommunicado threshold (0-20).")
    if old_rep < 20 and new_rep >= 20:
        effects.append("Reputation restored above excommunicado threshold.")
    if new_rep >= 90:
        effects.append("Reputation tier: Legendary. High Table takes notice.")
    elif new_rep >= 75:
        effects.append("Reputation tier: Trusted Operative.")

    return {
        "old_reputation": old_rep,
        "new_reputation": new_rep,
        "delta": delta,
        "reason": reason,
        "threshold_effects": effects,
    }


async def update_player_location(
    session_id: str,
    location_name: str,
) -> dict:
    """
    Move the player to a new location by name.

    Args:
        session_id: The session.
        location_name: Destination location name (matched case-insensitively).

    Returns:
        dict with new location details.
    """
    location = await fetch_one(
        "SELECT id, name, type, is_continental, is_neutral FROM locations WHERE lower(name) = lower($1)",
        location_name,
    )
    if not location:
        return {"error": f"Location '{location_name}' not found."}

    await execute(
        "UPDATE player_characters SET current_location_id = $1 WHERE session_id = $2",
        location["id"],
        session_id,
    )

    # Mirror to characters table
    player = await fetch_one(
        "SELECT character_id FROM player_characters WHERE session_id = $1", session_id
    )
    if player and player.get("character_id"):
        await execute(
            "UPDATE characters SET current_location_id = $1 WHERE id = $2",
            location["id"],
            player["character_id"],
        )

    return dict(location)


async def spend_gold(
    session_id: str,
    amount: int,
    reason: str,
) -> dict:
    """
    Deduct gold coins from the player's balance. Fails if insufficient.

    Args:
        session_id: The session.
        amount: Coins to spend (must be positive).
        reason: What the coins are for.

    Returns:
        dict with new_balance, spent, and reason. Error key if insufficient funds.
    """
    current = await fetch_val(
        "SELECT gold_coins FROM player_characters WHERE session_id = $1", session_id
    )
    if current is None:
        return {"error": "Player not found."}
    if current < amount:
        return {"error": f"Insufficient gold. Have {current}, need {amount}.", "current": current}

    new_balance = current - amount
    await execute(
        "UPDATE player_characters SET gold_coins = $1 WHERE session_id = $2",
        new_balance,
        session_id,
    )
    return {"new_balance": new_balance, "spent": amount, "reason": reason}


async def earn_gold(session_id: str, amount: int, reason: str) -> dict:
    """
    Add gold coins to the player's balance.

    Args:
        session_id: The session.
        amount: Coins to add.
        reason: Source of income.

    Returns:
        dict with new_balance and earned.
    """
    new_balance = await fetch_val(
        "UPDATE player_characters SET gold_coins = gold_coins + $1 WHERE session_id = $2 RETURNING gold_coins",
        amount,
        session_id,
    )
    return {"new_balance": new_balance, "earned": amount, "reason": reason}


# ── Missions ───────────────────────────────────────────────────────────────────


async def get_available_missions(
    session_id: str,
    limit: int = 3,
) -> list[dict]:
    """
    Return missions available to this player, filtered by reputation gate.

    The mission requirements JSONB may contain a min_reputation key.
    Missions are ordered by priority (high first) then age (oldest first).

    Args:
        session_id: The session.
        limit: Max missions to return (default 3 — Charon never overwhelms).

    Returns:
        List of mission dicts from available_missions_view.
    """
    player = await fetch_one(
        "SELECT reputation, faction_id FROM player_characters WHERE session_id = $1",
        session_id,
    )
    if not player:
        return []

    rep = player["reputation"]

    rows = await fetch_all(
        """
        SELECT *
        FROM available_missions_view
        WHERE COALESCE((requirements->>'min_reputation')::int, 0) <= $1
        ORDER BY priority DESC, id ASC
        LIMIT $2
        """,
        rep,
        limit,
    )
    return rows


async def accept_mission(session_id: str, mission_id: int) -> dict:
    """
    Assign a mission to the player and log it.

    Args:
        session_id: The session.
        mission_id: The mission to accept.

    Returns:
        Updated player state with mission details.
    """
    player = await fetch_one(
        "SELECT id, active_mission_id FROM player_characters WHERE session_id = $1",
        session_id,
    )
    if not player:
        return {"error": "Player not found."}
    if player["active_mission_id"]:
        return {"error": "You already have an active mission. Complete or abandon it first."}

    mission = await fetch_one(
        "SELECT * FROM missions WHERE id = $1 AND status = 'pending'", mission_id
    )
    if not mission:
        return {"error": f"Mission {mission_id} not available."}

    story_day = await fetch_val("SELECT current_day FROM story_state WHERE id = 1")

    async with transaction() as conn:
        # Assign in missions table
        await conn.execute(
            "UPDATE missions SET assigned_to_id = NULL, status = 'active' WHERE id = $1",
            mission_id,
        )
        # Link to player
        await conn.execute(
            "UPDATE player_characters SET active_mission_id = $1 WHERE session_id = $2",
            mission_id,
            session_id,
        )
        # Log it
        await conn.execute(
            """
            INSERT INTO player_mission_log (player_id, mission_id, offered_day, accepted_day)
            VALUES ($1, $2, $3, $3)
            """,
            player["id"],
            mission_id,
            story_day or 1,
        )

    return await fetch_one("SELECT * FROM player_status_view WHERE session_id = $1", session_id)


async def complete_mission(
    session_id: str,
    outcome: str,  # 'success' | 'failure' | 'abandoned' | 'complicated'
    narrative_outcome: str,
) -> dict:
    """
    Resolve the player's active mission and apply rewards/consequences.

    Rewards on success:
      - Gold coins: 3 + mission.priority coins
      - Reputation: +10 * (priority / 5)
      - Intel item if mission_type == 'rumor_check'

    Consequences on failure:
      - Reputation: -5 * priority
      - Possible debt creation

    Args:
        session_id: The session.
        outcome: How the mission ended.
        narrative_outcome: Text description for the scene memory.

    Returns:
        Resolution dict with rewards/consequences and updated player state.
    """
    player = await fetch_one(
        "SELECT id, active_mission_id, reputation FROM player_characters WHERE session_id = $1",
        session_id,
    )
    if not player or not player["active_mission_id"]:
        return {"error": "No active mission to complete."}

    mission = await fetch_one("SELECT * FROM missions WHERE id = $1", player["active_mission_id"])
    if not mission:
        return {"error": "Mission record not found."}

    story_day = await fetch_val("SELECT current_day FROM story_state WHERE id = 1") or 1
    rewards: dict = {}
    consequences: list = []

    if outcome == "success":
        gold_reward = 3 + mission["priority"]
        rep_delta = 5 * mission["priority"]
        rewards = {"gold": gold_reward, "reputation_delta": rep_delta}
    elif outcome == "failure":
        rep_delta = -(3 * mission["priority"])
        consequences = [f"Reputation -{abs(rep_delta)} for failed mission."]
        rewards = {"reputation_delta": rep_delta}
    else:  # complicated / abandoned
        rep_delta = -(1 * mission["priority"])
        consequences = ["Complications noted by the hotel management."]
        rewards = {"reputation_delta": rep_delta}

    async with transaction() as conn:
        # Update mission
        await conn.execute(
            "UPDATE missions SET status = $1, outcome = $2, completed_day = $3 WHERE id = $4",
            "completed" if outcome == "success" else outcome,
            narrative_outcome,
            story_day,
            mission["id"],
        )
        # Update player: clear active mission, bump counters
        counter_col = "missions_completed" if outcome == "success" else "missions_failed"
        await conn.execute(
            f"""
            UPDATE player_characters
            SET active_mission_id = NULL,
                gold_coins = gold_coins + $1,
                reputation = GREATEST(0, LEAST(100, reputation + $2)),
                {counter_col} = {counter_col} + 1
            WHERE session_id = $3
            """,
            rewards.get("gold", 0),
            rewards.get("reputation_delta", 0),
            session_id,
        )
        # Update mission log
        await conn.execute(
            """
            UPDATE player_mission_log
            SET completed_day = $1, outcome = $2, rewards_granted = $3, consequences = $4
            WHERE player_id = $5 AND mission_id = $6
            """,
            story_day,
            outcome,
            json.dumps(rewards),
            json.dumps(consequences),
            player["id"],
            mission["id"],
        )

    updated = await fetch_one("SELECT * FROM player_status_view WHERE session_id = $1", session_id)
    return {
        "outcome": outcome,
        "rewards": rewards,
        "consequences": consequences,
        "narrative": narrative_outcome,
        "player": updated,
    }


# ── Inventory ──────────────────────────────────────────────────────────────────


async def add_inventory_item(
    session_id: str,
    item_type: str,
    name: str,
    description: str,
    quantity: int = 1,
) -> dict:
    """
    Add an item to the player's inventory.

    Args:
        session_id: The session.
        item_type: One of: weapon, document, intel, vehicle, key, token, artifact, unknown.
        name: Item name.
        description: Brief description.
        quantity: How many.

    Returns:
        The created inventory row.
    """
    player_id = await fetch_val(
        "SELECT id FROM player_characters WHERE session_id = $1", session_id
    )
    if not player_id:
        return {"error": "Player not found."}

    story_day = await fetch_val("SELECT current_day FROM story_state WHERE id = 1") or 1

    row = await fetch_one(
        """
        INSERT INTO player_inventory (player_id, item_type, name, description, quantity, acquired_day)
        VALUES ($1, $2, $3, $4, $5, $6)
        RETURNING *
        """,
        player_id,
        item_type,
        name,
        description,
        quantity,
        story_day,
    )
    return row


async def get_inventory(session_id: str) -> list[dict]:
    """
    Return the player's full inventory.

    Args:
        session_id: The session.

    Returns:
        List of inventory items.
    """
    player_id = await fetch_val(
        "SELECT id FROM player_characters WHERE session_id = $1", session_id
    )
    if not player_id:
        return []
    return await fetch_all(
        "SELECT * FROM player_inventory WHERE player_id = $1 ORDER BY acquired_day, name",
        player_id,
    )


# ── Faction Standing ───────────────────────────────────────────────────────────


async def update_faction_standing(
    session_id: str,
    faction_name: str,
    delta: int,
    reason: str,
) -> dict:
    """
    Adjust the player's standing with a faction.

    Args:
        session_id: The session.
        faction_name: Faction to adjust (case-insensitive match).
        delta: Change amount.
        reason: Why it changed.

    Returns:
        dict with faction_name, old_standing, new_standing, delta.
    """
    player_id = await fetch_val(
        "SELECT id FROM player_characters WHERE session_id = $1", session_id
    )
    if not player_id:
        return {"error": "Player not found."}

    faction = await fetch_one(
        "SELECT id, name FROM factions WHERE lower(name) = lower($1)", faction_name
    )
    if not faction:
        return {"error": f"Faction '{faction_name}' not found."}

    old = (
        await fetch_val(
            "SELECT standing FROM player_faction_standing WHERE player_id = $1 AND faction_id = $2",
            player_id,
            faction["id"],
        )
        or 50
    )

    new_standing = max(0, min(100, old + delta))
    story_day = await fetch_val("SELECT current_day FROM story_state WHERE id = 1") or 1

    await execute(
        """
        INSERT INTO player_faction_standing (player_id, faction_id, standing, notes, last_change_day)
        VALUES ($1, $2, $3, $4, $5)
        ON CONFLICT (player_id, faction_id) DO UPDATE
            SET standing = $3, notes = $4, last_change_day = $5, updated_at = now()
        """,
        player_id,
        faction["id"],
        new_standing,
        reason,
        story_day,
    )

    return {
        "faction": faction["name"],
        "old_standing": old,
        "new_standing": new_standing,
        "delta": delta,
        "reason": reason,
    }
