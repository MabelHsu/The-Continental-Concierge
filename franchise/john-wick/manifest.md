# Franchise Bible: John Wick / The Continental

The demo franchise the engine ships with. Set in The Continental Hotel in
New York City, drawing on the underworld established in the *John Wick* films.

## Summary

- **Hub location:** The Continental Hotel (New York branch)
- **Host NPC:** Charon — head concierge
- **Currency:** Gold coins
- **Governing body:** The High Table
- **Core rule:** No business conducted on hotel grounds (violation → Adjudicator)
- **Tone:** Noir, understated, formally polite, undercurrent of lethal consequence

## Player archetypes

| Archetype | Starting Kit |
|-----------|-------------|
| Assassin | Suppressed pistol + clean passport |
| Cleaner | Burner phone + 7 gold coins |
| Fixer | Encrypted contact list + blank marker |
| Information Broker | Dossier fragment + encrypted drive |
| Weapons Dealer | Custom pistol + weapons cache key |
| Driver | Safecar + multiple IDs |
| Medic | Field kit + outstanding favor chip |
| Enforcer | Reinforced knuckles + employer letter |

## Files that constitute this bible

These are the only files that change when swapping franchises. Everything else
is engine code.

### Lore & World

- `db/seed_lore.sql`
  Characters (Charon, Winston, Sofia, Cassian, Bowery King, ...), factions
  (High Table, Ruska Roma, Camorra, Tarasov Mob, ...), locations (Continental
  lobby and bar, Red Circle, Theatre, ...), historical events, and the
  rulebook (no business on hotel grounds, markers, excommunicado, ...).

- `db/retrieval_views.sql`
  Views are franchise-agnostic, but `v_active_debts` and friends only make
  sense once the lore is seeded.

### Voice & Tone

- `app/agents/onboarding/prompt.md` — **Charon's check-in voice.** Formal,
  correct, never warm. Notes the register without comment. The single most
  franchise-specific file in the bible.

- `app/agents/narrator/prompt.md` — cinematic prose style for The Continental.
  Amber-and-leather lobby, people with business they don't discuss, the
  particular quiet of the hotel. Player is an operative; Charon is an NPC.

- `app/agents/archivist/prompt.md` — how lore is cited when answering
  "who is X" questions. Dossier-style, noir-inflected.

- `app/agents/ledger/prompt.md` — language around markers, debts, favors,
  and the weight system ("a marker of weight three").

- `app/agents/timeline/prompt.md` — scheduling and collision detection
  phrased in underworld terms ("the Adjudicator arrives at dusk").

- `app/agents/concierge/prompt.md` — routing instructions. Contains a
  small amount of franchise flavor (references Charon by name) but is
  mostly engine logic. Minor rewrite when swapping franchises.

### Player Config

- `app/shared/types.py`
  - `PlayerCharacter.archetype` — the eight roles above.
  - `OnboardingState.collected` — fields gathered in Charon's check-in.
  - Starting inventories are defined by the `create_player_character`
    function in `app/tools/player_tools.py`.

### Schema Labels

- `db/schema.sql`
  - Column `gold_coins` — rename in a comment only, the column itself is
    franchise-agnostic currency.
  - `factions` table — seeded with High Table, Ruska Roma, etc. Column
    names unchanged across franchises.
  - `rule_violations` severity levels (`minor`, `major`, `capital`) — the
    labels map to franchise-specific concepts (here: warning, debt,
    excommunicado).

## What you would change to fork this

To produce, say, a "Sci-Fi Station" bible:

1. `db/seed_lore.sql` → rewrite with station crew, corporations, dock rules.
2. `app/agents/onboarding/prompt.md` → ARIA (station AI) instead of Charon.
3. `app/agents/narrator/prompt.md` → orbital neon instead of lobby amber.
4. `app/shared/types.py` archetypes → Pilot, Engineer, Smuggler, Medic, ...
5. `app/tools/player_tools.py::create_player_character` → credit balances
   and starting kit per new archetype.
6. `db/schema.sql` → rename `gold_coins` comment to `credits`. No DDL change.

Everything else — orchestrator routing, consequence propagation, mission
loop, memory system, consistency checker, MCP toolbox, API layer —
stays the same.
