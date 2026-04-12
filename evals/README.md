# Evaluations

This folder tests the **engine**, not any specific franchise. Each eval asserts
a correctness property that must hold regardless of which franchise bible is
loaded.

The engine is a multi-agent narrative system, and "correctness" for such a
system has four failure modes. Each eval targets one:

| Eval | Failure mode it catches | When to run it |
|------|-------------------------|----------------|
| `agent_routing_eval.py` | Orchestrator routes a request to the wrong specialist agent (e.g. a debt query going to the Timeline). | After editing any `prompt.md` in `app/agents/` or changing routing rules in `concierge/prompt.md`. |
| `continuity_eval.py` | World state is forgotten across turns — a debt created on turn 2 doesn't affect the scene on turn 8. | After changing schema, `player_tools.py`, or the orchestrator's consequence-application logic. |
| `contradiction_eval.py` | The consistency checker misses an impossibility (character in two places at once, business conducted on consecrated ground, phantom debts referenced in narration). | After changing `consistency_tools.py` or the rule-violation pipeline. |
| `memory_retrieval_eval.py` | Hybrid search (keyword + vector) returns irrelevant chunks for a lore query, or misses a clearly relevant one. | After reseeding `lore_chunks`, changing the retrieval view, or editing `search_lore()`. |

## Running

These evals require a working AlloyDB connection (Omni locally, or cloud
AlloyDB via the Auth Proxy). See `to-do-list.md` Phase 2 for setup.

```bash
# Continuity, contradiction, and retrieval evals talk directly to the database
# via app/tools/db.py and don't need a deployed agent.
python -m evals.continuity_eval
python -m evals.contradiction_eval
python -m evals.memory_retrieval_eval

# Routing eval talks to a deployed Agent Engine and needs an agent ID.
python -m evals.agent_routing_eval \
  --agent-id $AGENT_ENGINE_ID \
  --project $GOOGLE_CLOUD_PROJECT \
  --region us-central1
```

## Agent routing eval notes

`agent_routing_eval.py` reads which sub-agents were invoked from ADK trace
events. The exact trace format depends on the ADK version — if `actual`
always comes back empty, the `extract_invoked_agents()` function needs to be
updated for the current ADK trace schema.

## What's not covered (yet)

The player-system evals listed in Phase 8b of `to-do-list.md` (onboarding
completion, mission loop, consequence propagation, reputation gates) are
not implemented yet — they're meant to be written alongside Phase 3, once the
tools are wired to real AlloyDB data.

## Adding a new eval

- Test one property. Don't write an eval that checks routing *and* continuity
  in the same function.
- Seed minimal state. If your test needs a specific character, create it in
  the test rather than relying on `seed_lore.sql` ordering.
- Clean up. Evals should be idempotent — running them twice should produce
  the same result.
- Return `EvalResult` (or the eval-specific result dataclass) so the summary
  printer works.
