# Phase 1d Test Guide — Onboarding Flow + Player Layer

**Agent**: `concierge_v3`
**Goal**: Verify the full onboarding gate, both character creation paths, the narrator POV flip, and the post-onboarding mission loop — all without AlloyDB.

---

## Setup

### 1. Install dependencies

```bash
pip install google-adk
```

### 2. Authenticate with Vertex AI

```bash
gcloud auth application-default login
```

Then confirm your `.env` has these three lines uncommented:

```dotenv
GOOGLE_GENAI_USE_VERTEXAI=TRUE
GOOGLE_CLOUD_PROJECT=the-continental-concierge
GOOGLE_CLOUD_LOCATION=us-central1
```

### 3. Configure your test scenario

Open `test_agents/concierge_v3/player_state.py` and set the two toggles at the top:

| Toggle | Value | Effect |
|--------|-------|--------|
| `MOCK_ONBOARDING_COMPLETE` | `False` | Start at hotel lobby, no identity yet |
| `MOCK_ONBOARDING_COMPLETE` | `True` | Skip onboarding, go straight to gameplay |
| `MOCK_PATH` | `"mystery"` | 5-step identity reveal (only used when False) |
| `MOCK_PATH` | `"custom"` | 4-step guided creation (only used when False) |

### 4. Launch ADK Dev UI

```bash
cd test_agents
adk web
```

Open `http://localhost:8000` in your browser. Select **concierge_v3** from the agent dropdown.

---

## Test A — Mystery Path (5 turns)

**Setup**: `MOCK_ONBOARDING_COMPLETE = False`, `MOCK_PATH = "mystery"`

This tests the identity-revelation arc: the player arrives as a blank slate and their character assembles itself through Charon's questions.

### Turn 1 — Arrival

**Type**: `I need a room.`

**What to verify**:
- Orchestrator called `get_player()` first (check Events panel)
- Routed to `onboarding` sub-agent (not narrator)
- Charon's opening line is a variant of: *"Good evening. Welcome to The Continental. How may I assist you?"*
- `_STATE["onboarding_step"]` advances to 1 after this exchange
- `creation_path` is set to `"mystery"` in `update_player()` call

**What failure looks like**:
- Narrator prose appears (long atmospheric description) → orchestrator skipped the onboarding gate
- No tool calls visible → agent responded without checking player state

---

### Turn 2 — The Alias

**Type**: `Call me Vega.`

**What to verify**:
- `update_player(alias="Vega", onboarding_step=1)` called
- Charon asks about origin: *"You've come a long way. Forgive me — your contact mentioned a city, but not which one."*
- Charon does NOT ask two questions at once

---

### Turn 3 — The Origin

**Type**: `I came from Prague.`

**What to verify**:
- `update_player(identity_clue="Arrived from Prague.", onboarding_step=2)` called
- Charon mentions the sealed envelope: *"There is a sealed envelope for you... an outstanding arrangement... weight of three."*

---

### Turn 4 — The Envelope

**Type**: `I'm aware. The arrangement was settled three years ago, as far as I'm concerned.`

**What to verify**:
- `update_player(identity_clue="[attitude toward debts — either dismissive or careful]", onboarding_step=3)` called
- Charon drops an NPC name (Winston, Sofia, or Berrada — should feel consistent with a Prague-based operative)
- Response ends with the NPC name question, nothing further

---

### Turn 5 — The Revelation

**Type**: `Sofia. Yes. That name means a great deal.`

**What to verify**:
- `update_player(identity_clue="[faction alliance with Sofia/Continental Management]", onboarding_step=4)` called
- Charon assembles an identity from the 4 clues: alias (Vega), origin (Prague), attitude toward debt, Sofia connection
- The assembled name feels *inevitable*, not arbitrary
- `update_player(name=<assembled_name>, archetype=<inferred>, backstory=<one sentence>)` called
- `complete_onboarding()` called — `onboarding_complete` flips to `True`
- Final line: *"Your suite is ready, [assembled name]. The Continental is always glad to have you home."*
- `identity_revealed` is `True` in state after this turn

**After Turn 5**: The orchestrator should now route all subsequent messages through the gameplay loop (narrator, not onboarding).

---

## Test B — Custom Path (4 turns)

**Setup**: `MOCK_ONBOARDING_COMPLETE = False`, `MOCK_PATH = "custom"`

This tests the direct declaration arc: the player knows who they are.

### Turn 1 — Arrival

**Type**: `I'm expected.`

**What to verify**:
- Routes to `onboarding` sub-agent
- Charon's line: *"Good evening. Your name, for the register."*
- `creation_path` set to `"custom"`

---

### Turn 2 — The Name

**Type**: `My name is Reyes. Marcus Reyes.`

**What to verify**:
- `update_player(name="Marcus Reyes", onboarding_step=1)` called
- Charon asks profession: *"And your profession? The hotel likes to know how best to serve its guests."*

---

### Turn 3 — The Profession

**Type**: `I'm a cleaner.`

**What to verify**:
- `update_player(archetype="cleaner", onboarding_step=2)` called
- Archetype normalized (e.g. "hitman" → "assassin", "fixer", etc.)
- Charon asks affiliation: *"Your primary affiliation — for the ledger."*

---

### Turn 4 — Affiliation and Marker

**Type**: `Independent. No outstanding arrangements.`

**What to verify**:
- `update_player(faction_name="Independent", onboarding_step=3)` called
- `complete_onboarding()` called
- Final line includes floor and dining/bar info: *"Your suite is on the [floor]. Dinner is served until midnight. The bar, as always, is open."*
- `_STATE["inventory"]` seeded with cleaner kit: burner phone + 7 gold coins
- `onboarding_complete` is `True`

---

## Test C — Narrator POV Flip (post-onboarding)

**Setup**: `MOCK_ONBOARDING_COMPLETE = True`

This is the most important qualitative test. Verify the player is their *character* in the world, not the concierge.

### Turn 1 — World query

**Type**: `Tell me about the High Table.`

**What to verify**:

✅ **Correct (v3)**:
> *"The bar hums with quiet conversation. You settle into a corner seat. Charon appears at the edge of the room — not approaching, simply present."*
> *"The High Table is not a body you address. It is a weight that presses on every transaction in this world."*

❌ **Wrong (v2 regression)**:
> *"You, the concierge, receive a question from a guest about the High Table..."*
> *"As the concierge, you explain..."*

**What to also verify**:
- Narrator called `get_player()` first (Events panel)
- Narrator called `get_charon_voice()` before writing any Charon dialogue
- Scene ends with 2–4 "What you can do next:" options written as prose fragments, not a menu
- No JSON, no field labels, no "According to my data..."

---

### Turn 2 — Social query

**Type**: `What do you know about the Tarasov organization?`

**What to verify**:
- Orchestrator routes to `ledger` tool (AgentTool — data returned to orchestrator)
- Orchestrator then transfers to `narrator` with ledger results
- Narrator writes in second person: *"You"*, not *"The concierge"*
- Charon is present as an NPC, not the player's role

---

### Turn 3 — Situation query

**Type**: `What's the current situation in the hotel?`

**What to verify**:
- Orchestrator routes to `timeline` tool
- Narrator calls `get_atmosphere(crisis_level)` with the crisis level from the handoff
- Atmospheric calibration visible: crisis 4 → tense, "building urgency", medium-length sentences

---

## Test D — Mission Loop

**Setup**: `MOCK_ONBOARDING_COMPLETE = True`

### Step 1 — Ask for work

**Type**: `Do you have anything for me tonight?`

**What to verify**:
- Orchestrator calls `get_available_missions(session_id="test-session-001")`
- Returns up to 3 missions (Osaka, Package, Casablanca — all should be available at rep 55)
- Narrator renders Charon presenting missions as *discreet suggestions*, never explicit contracts
- Language check: no "kill", no "murder", no "assassination" — use euphemisms
- A folded note slide, a lean-in, or a quiet word — based on priority level

---

### Step 2 — Accept a mission

**Type**: `I'll take the Osaka matter.`

**What to verify**:
- Orchestrator calls `accept_mission(session_id="test-session-001", mission_id=1)`
- `_STATE["active_mission_title"]` = "The Osaka Arrangement"
- Narrator renders Charon's acknowledgment: *one line, no fanfare*
- Mission tension should appear in subsequent narrator descriptions

---

### Step 3 — Complete the mission

**Type**: `The matter in Osaka is concluded.`

**What to verify**:
- Orchestrator calls `complete_mission(session_id="test-session-001", outcome="success")`
- `_STATE["gold_coins"]` increases by 5
- `_STATE["reputation"]` increases by 10 (55 → 65)
- `_STATE["active_mission_title"]` is `None`
- Narrator renders the reward scene: gold changes hands without comment
- Charon acknowledges — no fanfare, no explicit "you killed him"

---

## Test E — Edge Cases

### E1 — Double mission acceptance

**Type**: *(with active mission)* `I'll take the Casablanca job too.`

**What to verify**:
- `accept_mission()` returns `{"error": "You already have an active mission. Resolve it first."}`
- Narrator renders Charon declining gracefully — no error message exposed to player

---

### E2 — Onboarding gate doesn't leak

**Setup**: `MOCK_ONBOARDING_COMPLETE = False`

**Type**: `Tell me about the High Table.` *(before onboarding completes)*

**What to verify**:
- Orchestrator routes to `onboarding` (not to archivist + narrator)
- Charon asks the *current onboarding question*, not lore
- No lore is provided until onboarding is complete

---

### E3 — Session ID consistency

All tool calls in the Events panel should show `session_id="test-session-001"`. If any tool call omits the session ID or uses a different value, the routing is broken.

---

## What to Look for in the Events Panel

The ADK Dev UI Events panel shows every tool call and agent transfer. A healthy v3 turn looks like:

```
concierge_v3
  → get_player("test-session-001")          ← always first
  → [if onboarding_complete False]
      → transfer_to_agent("onboarding")
  → [if onboarding_complete True]
      → archivist / ledger / timeline        ← data agents return here
      → transfer_to_agent("narrator")        ← final, always

narrator
  → get_player("test-session-001")
  → get_charon_voice()
  → get_atmosphere(4)
  [prose output]
```

**Red flags**:
- `get_player()` not the first call → routing may ignore onboarding state
- Narrator called before data agents return → orchestrator didn't wait for data
- Narrator output is JSON or has field labels → output format rules not followed
- `narrator` called during onboarding → onboarding gate broken

---

## Common Issues

### "The agent transferred to narrator during onboarding"

The orchestrator's Step 1 instruction must be absolute: `IF onboarding_complete == False → transfer to onboarding. Do not call any other tools.`

Check: does `get_player()` show `onboarding_complete: false` in Events? If yes and it still went to narrator, the orchestrator instruction isn't strong enough. Add explicit emphasis to the Step 1 block in `agent.py`.

---

### "Charon is writing long prose paragraphs"

The onboarding agent's output rule: "Write ONLY Charon's spoken line. Nothing else." Max tokens is 512 to enforce this. If Charon is writing essays, check `max_output_tokens` in `onboarding.py`.

---

### "The narrator is writing in first person or calling the player 'the concierge'"

This is the v2 regression. Check `narrator.py` instruction — the WRONG vs RIGHT examples must be present. The key phrase: *"You are not the concierge. The player is their character."*

---

### "State doesn't persist between turns"

The `_STATE` dict in `player_state.py` is module-level. Within a single ADK session, it persists. If state resets between turns, ADK may be reimporting the module. Confirm with a print statement: `print(_STATE["onboarding_step"])` in `get_player()`.

---

### "Mission 3 (Casablanca Fragment) not appearing"

Casablanca requires `min_reputation: 50`. Default rep when `MOCK_ONBOARDING_COMPLETE = True` is 55, so it should appear. If not, check `get_available_missions()` filter logic.

---

## After Phase 1d — What's Next

Once all five tests pass and the ADK Events panel shows clean routing:

**Phase 2a** — Connect AlloyDB. Replace `player_state.py` mock functions with calls to `app/tools/player_tools.py` (asyncpg). Run the schema migration.

**Phase 2b** — Connect Archivist/Ledger/Timeline to real MCP Toolbox queries (replace mock functions in v2/v3 with actual DB reads).

**Phase 2c** — Deploy to Vertex AI Agent Engine. Smoke test with the `/chat` endpoint via FastAPI.

**Phase 2d** — Evaluate narrator output quality against the voice spec. Tune temperature and instructions based on 20+ test sessions.
