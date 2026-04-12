"""
Contradiction Eval
===================
Tests that the system correctly detects and prevents contradictions:
- Characters in two places at once.
- Business on consecrated ground.
- Phantom debts (referenced but nonexistent).
- Deceased characters acting.
- Timeline impossibilities.
"""

import asyncio
from dataclasses import dataclass

import pytest

# Phase-3 tool layer guard — see memory_retrieval_eval.py for the rationale.
# `execute_returning` is not yet exported by `app.tools.db` (that module
# currently exposes `fetch_all`, `fetch_one`, `fetch_val`, `execute`,
# `execute_many`, `transaction`). The try/except keeps `pytest evals/`
# collectable; the skip marker below makes pytest skip this file cleanly
# until Phase 3 grows `execute_returning`.
try:
    from app.tools.consistency_tools import check_consistency  # noqa: F401
    from app.tools.db import (  # noqa: F401
        execute,
        execute_returning,
        fetch_all,
        fetch_one,
    )

    _PHASE3_READY = True
    _PHASE3_SKIP_REASON = ""
except ImportError as _import_err:
    _PHASE3_READY = False
    _PHASE3_SKIP_REASON = f"Phase 3 tool layer not ready: {_import_err}"

pytestmark = pytest.mark.skipif(
    not _PHASE3_READY,
    reason=_PHASE3_SKIP_REASON,
)


@dataclass
class EvalResult:
    name: str
    passed: bool
    details: str


async def eval_detects_location_collision() -> EvalResult:
    """
    Test: System flags when a character is placed in two simultaneous events
    at different locations.
    """
    sofia = await fetch_one("SELECT id FROM characters WHERE name = 'Sofia Al-Azwar'")
    loc1 = await fetch_one(
        "SELECT id FROM locations WHERE name LIKE '%New York%' AND type = 'continental'"
    )
    loc2 = await fetch_one("SELECT id FROM locations WHERE name = 'The Red Circle'")

    # Create two simultaneous events with Sofia at different locations
    await execute(
        """
        INSERT INTO events (story_day, story_time, title, description, location_id,
                           event_type, participants, is_public, turn_number)
        VALUES (99, 'evening', 'Test Event A', 'Sofia at Continental', $1,
                'meeting', ARRAY[$2]::uuid[], TRUE, 999)
        """,
        loc1["id"],
        sofia["id"],
    )
    await execute(
        """
        INSERT INTO events (story_day, story_time, title, description, location_id,
                           event_type, participants, is_public, turn_number)
        VALUES (99, 'evening', 'Test Event B', 'Sofia at Red Circle', $1,
                'social', ARRAY[$2]::uuid[], TRUE, 999)
        """,
        loc2["id"],
        sofia["id"],
    )

    # Check timeline conflicts
    conflicts = await fetch_all("SELECT * FROM timeline_conflicts WHERE story_day = 99")

    passed = len(conflicts) > 0 and any(c["character_name"] == "Sofia Al-Azwar" for c in conflicts)

    # Cleanup
    await execute("DELETE FROM events WHERE story_day = 99")

    return EvalResult(
        name="location_collision_detection",
        passed=passed,
        details=f"Conflicts found: {len(conflicts)}, Sofia flagged: {passed}",
    )


async def eval_detects_consecrated_ground_violation() -> EvalResult:
    """
    Test: System flags business/conflict at consecrated locations.
    """
    result = check_consistency(
        narrative="Cassian drew his weapon in the Continental lobby.",
        characters=["Cassian"],
        story_day=1,
        story_time="evening",
        location="The Continental — New York",
        state_changes={"conflict": True},
    )

    passed = not result["passed"] or any(
        i["type"] == "consecrated_ground_violation" for i in result["issues"]
    )

    return EvalResult(
        name="consecrated_ground_violation",
        passed=passed,
        details=f"Issues: {result['issue_count']}, Warnings: {result['warning_count']}",
    )


async def eval_detects_deceased_character() -> EvalResult:
    """
    Test: System flags when a deceased character appears in a scene.
    """
    # Temporarily kill a character
    await execute("UPDATE characters SET status = 'deceased' WHERE name = 'Cassian'")

    result = check_consistency(
        narrative="Cassian walked into the lobby and ordered a drink.",
        characters=["Cassian"],
        story_day=1,
        story_time="evening",
        location="The Continental — New York",
        state_changes={},
    )

    passed = any(i["type"] == "deceased_character_active" for i in result["issues"])

    # Restore
    await execute("UPDATE characters SET status = 'active' WHERE name = 'Cassian'")

    return EvalResult(
        name="deceased_character_detection",
        passed=passed,
        details=f"Deceased flag raised: {passed}, Issues: {result['issues']}",
    )


async def eval_detects_phantom_debt() -> EvalResult:
    """
    Test: System warns when narrative references debts that don't exist.
    """
    result = check_consistency(
        narrative="Akira called in the marker that Charon owed her, demanding safe passage.",
        characters=["Akira Shimazu", "Charon"],
        story_day=1,
        story_time="morning",
        location="The Continental — New York",
        state_changes={},
    )

    # Check if phantom debt warning is raised
    # (Akira has a debt TO the Adjudicator, not FROM Charon)
    phantom_warnings = [w for w in result["warnings"] if w["type"] == "phantom_debt_reference"]

    passed = len(phantom_warnings) > 0

    return EvalResult(
        name="phantom_debt_detection",
        passed=passed,
        details=f"Phantom debt warnings: {len(phantom_warnings)}",
    )


async def eval_detects_excommunicado_on_grounds() -> EvalResult:
    """
    Test: System warns when an excommunicado character is at a Continental.
    """
    await execute("UPDATE characters SET status = 'excommunicado' WHERE name = 'Bowery King'")

    result = check_consistency(
        narrative="The Bowery King strode into the Continental lobby.",
        characters=["Bowery King"],
        story_day=1,
        story_time="evening",
        location="The Continental — New York",
        state_changes={},
    )

    excom_warnings = [w for w in result["warnings"] if w["type"] == "excommunicado_on_grounds"]

    passed = len(excom_warnings) > 0

    # Restore
    await execute("UPDATE characters SET status = 'active' WHERE name = 'Bowery King'")

    return EvalResult(
        name="excommunicado_detection",
        passed=passed,
        details=f"Excommunicado warnings: {len(excom_warnings)}",
    )


async def run_all_evals():
    """Run all contradiction evaluations."""
    print("=" * 60)
    print("CONTRADICTION EVALUATION SUITE")
    print("=" * 60)

    evals = [
        eval_detects_location_collision,
        eval_detects_consecrated_ground_violation,
        eval_detects_deceased_character,
        eval_detects_phantom_debt,
        eval_detects_excommunicado_on_grounds,
    ]

    results = []
    for eval_fn in evals:
        try:
            result = await eval_fn()
            results.append(result)
            status = "PASS" if result.passed else "FAIL"
            print(f"  [{status}] {result.name}: {result.details}")
        except Exception as e:
            results.append(
                EvalResult(
                    name=eval_fn.__name__,
                    passed=False,
                    details=f"Exception: {e}",
                )
            )
            print(f"  [ERROR] {eval_fn.__name__}: {e}")

    total = len(results)
    passed_count = sum(1 for r in results if r.passed)
    print(f"\nResults: {passed_count}/{total} passed")
    print("=" * 60)

    return results


if __name__ == "__main__":
    asyncio.run(run_all_evals())
