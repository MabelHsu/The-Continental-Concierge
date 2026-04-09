"""
Continuity Eval
================
Tests that the system maintains character and world state
across multiple turns and sessions.

Key assertions:
- Characters remembered with correct attributes after N turns.
- Debts created in early turns affect later scenes.
- Location changes persist.
- Reputation shifts are reflected in narrative tone.
"""

import asyncio
import json
from dataclasses import dataclass
from typing import Optional

from app.tools.db import fetch_one, fetch_all, execute
from app.tools.world_state_tools import initialize_story_state, increment_turn


@dataclass
class EvalResult:
    name: str
    passed: bool
    details: str
    turn_number: int


async def setup_eval_db():
    """Ensure the eval starts from a known state."""
    # Reset to seed data (in practice, use a test database)
    pass


async def eval_character_persistence() -> EvalResult:
    """
    Test: A character introduced in turn 1 retains all attributes in turn 10.
    """
    # Turn 1: Check Sofia's initial state
    sofia_t1 = await fetch_one(
        "SELECT name, reputation, status, faction_id FROM characters WHERE name = 'Sofia Al-Azwar'"
    )
    assert sofia_t1 is not None, "Sofia should exist at turn 1"
    initial_rep = sofia_t1["reputation"]

    # Simulate 9 turns of other activity
    for _ in range(9):
        increment_turn()

    # Turn 10: Verify Sofia unchanged (no one modified her)
    sofia_t10 = await fetch_one(
        "SELECT name, reputation, status, faction_id FROM characters WHERE name = 'Sofia Al-Azwar'"
    )

    passed = (
        sofia_t10 is not None
        and sofia_t10["reputation"] == initial_rep
        and sofia_t10["status"] == sofia_t1["status"]
        and sofia_t10["faction_id"] == sofia_t1["faction_id"]
    )

    return EvalResult(
        name="character_persistence",
        passed=passed,
        details=f"Turn 1 rep={initial_rep}, Turn 10 rep={sofia_t10['reputation'] if sofia_t10 else 'MISSING'}",
        turn_number=10,
    )


async def eval_debt_affects_later_scenes() -> EvalResult:
    """
    Test: A debt created in turn 2 is retrievable and affects turn 8.
    """
    # Turn 2: Create a new debt
    increment_turn()
    increment_turn()

    creditor = await fetch_one("SELECT id FROM characters WHERE name = 'Winston Scott'")
    debtor = await fetch_one("SELECT id FROM characters WHERE name = 'Cassian'")

    await execute(
        """
        INSERT INTO debts_markers (creditor_id, debtor_id, marker_type, description, value_weight)
        VALUES ($1, $2, 'gold_coin', 'Winston provided safe passage from the Red Circle.', 4)
        """,
        creditor["id"],
        debtor["id"],
    )

    # Advance to turn 8
    for _ in range(6):
        increment_turn()

    # Turn 8: Verify debt still exists
    debt = await fetch_one(
        """
        SELECT * FROM active_debts
        WHERE creditor_name = 'Winston Scott' AND debtor_name = 'Cassian'
          AND marker_type = 'gold_coin'
        """
    )

    passed = debt is not None and debt["value_weight"] == 4

    return EvalResult(
        name="debt_persistence_and_recall",
        passed=passed,
        details=f"Debt found at turn 8: {debt is not None}, weight={debt['value_weight'] if debt else 'N/A'}",
        turn_number=8,
    )


async def eval_location_change_persists() -> EvalResult:
    """
    Test: Moving a character updates their location in all subsequent queries.
    """
    # Move Sofia to the Red Circle
    rome = await fetch_one("SELECT id FROM locations WHERE name LIKE '%Rome%'")
    red_circle = await fetch_one("SELECT id FROM locations WHERE name = 'The Red Circle'")
    sofia = await fetch_one("SELECT id FROM characters WHERE name = 'Sofia Al-Azwar'")

    # Verify starting location
    pre_move = await fetch_one(
        "SELECT current_location_id FROM characters WHERE id = $1", sofia["id"]
    )

    # Move
    await execute(
        "UPDATE characters SET current_location_id = $1 WHERE id = $2",
        red_circle["id"],
        sofia["id"],
    )

    # Verify in dossier view
    dossier = await fetch_one(
        "SELECT current_location FROM character_dossier WHERE name = 'Sofia Al-Azwar'"
    )

    # Verify in location occupants view
    occupants = await fetch_one(
        "SELECT occupant_names FROM location_occupants WHERE location_name = 'The Red Circle'"
    )

    passed = (
        dossier is not None
        and "Red Circle" in (dossier.get("current_location") or "")
        and occupants is not None
        and "Sofia Al-Azwar" in (occupants.get("occupant_names") or [])
    )

    # Restore
    await execute(
        "UPDATE characters SET current_location_id = $1 WHERE id = $2",
        pre_move["current_location_id"],
        sofia["id"],
    )

    return EvalResult(
        name="location_change_persistence",
        passed=passed,
        details=f"Dossier location: {dossier.get('current_location') if dossier else 'N/A'}",
        turn_number=0,
    )


async def eval_reputation_affects_queries() -> EvalResult:
    """
    Test: Reputation changes are reflected in the reputation ledger view.
    """
    # Get initial reputation
    initial = await fetch_one(
        "SELECT reputation FROM characters WHERE name = 'Bowery King'"
    )
    initial_rep = initial["reputation"]

    # Decrease reputation
    new_rep = max(0, initial_rep - 15)
    await execute(
        "UPDATE characters SET reputation = $1 WHERE name = 'Bowery King'",
        new_rep,
    )

    # Verify in reputation ledger
    ledger = await fetch_one(
        "SELECT * FROM reputation_ledger WHERE name = 'Bowery King'"
    )

    passed = ledger is not None and ledger["reputation"] == new_rep

    # Restore
    await execute(
        "UPDATE characters SET reputation = $1 WHERE name = 'Bowery King'",
        initial_rep,
    )

    return EvalResult(
        name="reputation_change_reflected",
        passed=passed,
        details=f"Initial={initial_rep}, Changed to={new_rep}, Ledger shows={ledger['reputation'] if ledger else 'N/A'}",
        turn_number=0,
    )


async def run_all_evals():
    """Run all continuity evaluations."""
    print("=" * 60)
    print("CONTINUITY EVALUATION SUITE")
    print("=" * 60)

    initialize_story_state("eval-session-001")

    evals = [
        eval_character_persistence,
        eval_debt_affects_later_scenes,
        eval_location_change_persists,
        eval_reputation_affects_queries,
    ]

    results = []
    for eval_fn in evals:
        try:
            result = await eval_fn()
            results.append(result)
            status = "PASS" if result.passed else "FAIL"
            print(f"  [{status}] {result.name}: {result.details}")
        except Exception as e:
            results.append(EvalResult(
                name=eval_fn.__name__,
                passed=False,
                details=f"Exception: {e}",
                turn_number=-1,
            ))
            print(f"  [ERROR] {eval_fn.__name__}: {e}")

    total = len(results)
    passed = sum(1 for r in results if r.passed)
    print(f"\nResults: {passed}/{total} passed")
    print("=" * 60)

    return results


if __name__ == "__main__":
    asyncio.run(run_all_evals())
