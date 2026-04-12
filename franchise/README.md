# Franchise Bibles

Each subdirectory here is a **franchise bible** — the portable bundle of lore, voice,
and configuration that makes the Narrative Engine feel like a specific IP.

Everything outside this directory (the orchestrator, agents, player state machine,
consequence propagation, mission loop, memory system, database layer, API) is
**franchise-agnostic** and stays the same across deployments.

## What lives in a franchise bible

A franchise bible is a manifest plus pointers into four layers of the codebase:

| Layer | Where it lives | What it defines |
|-------|----------------|-----------------|
| **Lore & World** | `db/seed_lore.sql` | Characters, factions, locations, history, rules |
| **Voice & Tone** | `app/agents/*/prompt.md` | NPC personality, prose style, world-specific language |
| **Player Config** | `app/shared/types.py` | Archetypes, stat names, starting inventories |
| **Schema Labels** | `db/schema.sql` | Currency name, faction terminology, rule categories |

The manifest in each franchise folder tells you **exactly which files constitute
that franchise**, so you can swap bibles cleanly.

## Currently shipped

- **[john-wick/](john-wick/)** — The Continental Hotel, Charon, the High Table.
  This is the demo franchise the engine ships with.

## Adding a new franchise

1. Copy `john-wick/` to `your-franchise/` and update `manifest.md`.
2. Rewrite `db/seed_lore.sql` with your world's characters, factions, locations, rules.
3. Rewrite each `app/agents/*/prompt.md` in your world's voice.
4. Update `app/shared/types.py` with your archetypes and starting inventories.
5. Rename currency and faction terminology in `db/schema.sql` comments — the column
   names (`gold_coins`, `factions`) stay the same; only user-facing labels change.
6. Re-run `db/seed_embeddings.py` to vectorise your new lore.
7. Test with `adk web test_agents/` before deploying.

No orchestrator, no routing logic, no consequence engine touched.
