"""
Memory Retrieval Eval
======================
Tests the quality of AlloyDB hybrid search for lore retrieval.
Verifies that the combination of keyword + vector search
returns relevant results for different query types.

Query categories tested:
1. Exact match (character name, rule number)
2. Semantic (thematic, conceptual)
3. Mixed (structured fact + semantic context)
4. Cross-reference (connecting entities via relationships)
"""

import asyncio
from dataclasses import dataclass

import pytest

# Phase-3 tool layer guard.
# `generate_embedding` and `get_character_dossier` are part of the real
# lore/retrieval implementation that lands in Phase 3 (hybrid search +
# Vertex AI embeddings). Until then the imports fail, which used to break
# `pytest evals/` at collection time. The try/except keeps the module
# importable; the pytestmark below skips the whole file cleanly instead
# of crashing the test runner. Delete both once Phase 3 is merged.
try:
    from app.tools.lore_tools import search_lore, get_character_dossier  # noqa: F401
    from app.tools.db import fetch_all, generate_embedding  # noqa: F401
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
class RetrievalTestCase:
    name: str
    query: str
    expected_contains: list[str]  # Keywords that MUST appear in results
    category_filter: str = None
    min_results: int = 1
    description: str = ""


@dataclass
class RetrievalResult:
    name: str
    passed: bool
    result_count: int
    matched_keywords: list[str]
    missing_keywords: list[str]
    details: str


# ── Test Cases ────────────────────────────────────────────────

RETRIEVAL_TEST_CASES = [
    # Exact / keyword-heavy
    RetrievalTestCase(
        name="exact_character_lore",
        query="role of the concierge at the Continental",
        expected_contains=["concierge", "continental"],
        description="Should find the lore chunk about the Concierge role.",
    ),
    RetrievalTestCase(
        name="exact_rule_search",
        query="no business on Continental grounds rule",
        expected_contains=["business", "continental"],
        category_filter="rule",
        description="Should find Rule 1 about no business on grounds.",
    ),
    RetrievalTestCase(
        name="exact_location_search",
        query="The Red Circle nightclub",
        expected_contains=["red circle", "nightclub"],
        description="Should find the Red Circle lore chunk.",
    ),

    # Semantic / conceptual
    RetrievalTestCase(
        name="semantic_debt_concept",
        query="what happens when someone refuses to honor an obligation",
        expected_contains=["marker", "debt"],
        description="Should find marker system lore via semantic similarity.",
    ),
    RetrievalTestCase(
        name="semantic_punishment",
        query="ultimate sanction for breaking the rules",
        expected_contains=["excommunicado"],
        description="Should find excommunicado lore via semantic match.",
    ),
    RetrievalTestCase(
        name="semantic_economy",
        query="how does payment work in the underworld",
        expected_contains=["gold coin", "currency"],
        description="Should find gold coin economy lore.",
    ),

    # Mixed queries (structured + semantic)
    RetrievalTestCase(
        name="mixed_casablanca",
        query="diplomatic crisis involving Sofia in North Africa",
        expected_contains=["casablanca", "sofia"],
        description="Should connect Sofia + diplomatic crisis to Casablanca Incident.",
    ),
    RetrievalTestCase(
        name="mixed_high_table_power",
        query="who governs the assassin organizations worldwide",
        expected_contains=["high table", "governing"],
        description="Should find High Table faction lore.",
    ),

    # Cross-reference (entity connections)
    RetrievalTestCase(
        name="cross_ref_sofia_debts",
        query="what does Sofia owe and to whom",
        expected_contains=["sofia", "winston"],
        description="Should connect Sofia's debts to Winston via dossier.",
    ),
]


# ── Evaluation Runner ─────────────────────────────────────────

async def evaluate_retrieval() -> list[RetrievalResult]:
    """Run retrieval quality evaluation."""
    results = []

    for tc in RETRIEVAL_TEST_CASES:
        try:
            # For cross-reference queries, use dossier lookup
            if tc.name.startswith("cross_ref"):
                # Extract character name from expected
                search_result = get_character_dossier(tc.expected_contains[0].title())
                result_text = str(search_result).lower()
            else:
                # Use hybrid lore search
                search_result = search_lore(
                    query=tc.query,
                    category=tc.category_filter,
                    limit=5,
                )
                # Concatenate all result content for keyword checking
                result_text = " ".join(
                    r.get("content", "") + " " + r.get("title", "")
                    for r in search_result.get("results", [])
                ).lower()

            # Check which expected keywords appear
            matched = [
                kw for kw in tc.expected_contains
                if kw.lower() in result_text
            ]
            missing = [
                kw for kw in tc.expected_contains
                if kw.lower() not in result_text
            ]

            result_count = (
                search_result.get("result_count", 0)
                if isinstance(search_result, dict) and "result_count" in search_result
                else 1 if search_result else 0
            )

            passed = (
                len(missing) == 0
                and result_count >= tc.min_results
            )

            results.append(RetrievalResult(
                name=tc.name,
                passed=passed,
                result_count=result_count,
                matched_keywords=matched,
                missing_keywords=missing,
                details=f"Found {result_count} results. Matched: {matched}, Missing: {missing}",
            ))

        except Exception as e:
            results.append(RetrievalResult(
                name=tc.name,
                passed=False,
                result_count=0,
                matched_keywords=[],
                missing_keywords=tc.expected_contains,
                details=f"Error: {e}",
            ))

    return results


def print_summary(results: list[RetrievalResult]):
    """Print retrieval evaluation summary."""
    print("=" * 60)
    print("MEMORY RETRIEVAL EVALUATION SUITE")
    print("=" * 60)

    for r in results:
        status = "PASS" if r.passed else "FAIL"
        print(f"  [{status}] {r.name}")
        if not r.passed:
            print(f"         Results: {r.result_count}, Missing: {r.missing_keywords}")

    total = len(results)
    passed = sum(1 for r in results if r.passed)
    print(f"\nResults: {passed}/{total} passed")

    # Categorize failures
    semantic_fails = [r for r in results if not r.passed and "semantic" in r.name]
    exact_fails = [r for r in results if not r.passed and "exact" in r.name]
    mixed_fails = [r for r in results if not r.passed and "mixed" in r.name]

    if semantic_fails:
        print(f"\nSemantic search failures ({len(semantic_fails)}):")
        print("  → Consider re-embedding lore with a better model or adding more content.")
    if exact_fails:
        print(f"\nExact search failures ({len(exact_fails)}):")
        print("  → Check full-text search index and keyword coverage.")
    if mixed_fails:
        print(f"\nMixed query failures ({len(mixed_fails)}):")
        print("  → Adjust RRF weights (keyword_weight vs vector_weight) in hybrid_lore_search().")

    print("=" * 60)


if __name__ == "__main__":
    results = asyncio.run(evaluate_retrieval())
    print_summary(results)
