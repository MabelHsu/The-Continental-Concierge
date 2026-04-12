# The Continental Concierge

An AI-powered **Narrative Engine** that turns any franchise into a persistent, interactive world — where fans become characters and every choice has consequences.

> **Demo franchise:** The Continental, from the *John Wick* universe.

Built on the Google Cloud stack: **ADK** (Agent Development Kit), **Vertex AI Agent Engine**, **AlloyDB**, **Cloud Run**, and **MCP Toolbox for Databases**.

---

> **Below:** The following walkthrough shows the engine loaded with John Wick franchise content.

## The Game

You play as an operative in the underworld — an assassin, fixer, cleaner, information broker, or one of several other archetypes. You have just arrived at The Continental Hotel in New York City.

**Charon** is the head concierge. He is your primary contact in the hotel. He offers information, missions, and the particular kind of help that only the hotel can provide. He is always at the desk. He always knows more than he says.

The world around you is alive: NPCs have relationships, debts, and agendas. Factions accumulate and lose influence. Events ripple through the timeline. Your choices have consequences that persist.

### Two Ways to Begin

**"I need a room."** — Mystery Identity path. You arrive without a clear record. Over five exchanges with Charon, your identity assembles itself from fragments — a city you came from, a name someone left for you, a reaction to a face you shouldn't recognise. Who you are emerges from what you know.

**"I'm expected."** — Custom Creation path. You know who you are. Four exchanges with Charon: your name, your profession, your affiliation, any outstanding arrangements with the house. Formal. Efficient. The hotel appreciates clarity.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      You (the Operative)                        │
│         "Ask Charon what work is available tonight."            │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│                Concierge Orchestrator                            │
│          (Vertex AI Agent Engine / Gemini 2.5 Pro)               │
│                                                                  │
│  1. Check player state (onboarding complete?)                    │
│  2. Parse request — what does the player want?                   │
│  3. Route to specialists (parallel where safe)                   │
│  4. Apply player consequences (reputation, gold, location)       │
│  5. Consistency check                                            │
│  6. Hand to Narrative Director for cinematic response            │
└──────┬────────┬───────────┬─────────┬──────────┬─────────────────┘
       │        │           │         │          │
       ▼        ▼           ▼         ▼          ▼
  ┌──────────┐┌────────┐ ┌────────┐┌────────┐┌──────────┐
  │Onboarding││Archiv- │ │ Ledger ││Timeline││ Narrator │
  │  Agent   ││  ist   │ │ Agent  ││ Agent  ││  Agent   │
  │ (Charon) ││(Flash) │ │(Flash) ││(Flash) ││  (Pro)   │
  └────┬─────┘└──┬─────┘ └───┬────┘└───┬────┘└─────┬────┘
       │         │           │         │           │
       └─────────┴───────────┴─────────┴───────────┘
                             │
              ┌──────────────┴──────────────┐
              ▼                             ▼
   ┌──────────────────┐       ┌─────────────────────────┐
   │   MCP Toolbox    │       │    Custom World MCP      │
   │  (Read-only DB)  │       │   (Write operations)     │
   └────────┬─────────┘       └───────────┬─────────────┘
            └──────────────┬──────────────┘
                           ▼
                 ┌──────────────────┐
                 │     AlloyDB      │
                 │                  │
                 │  Operational     │  characters, factions, debts,
                 │  State           │  events, missions, rules
                 │                  │
                 │  Player Layer    │  player_characters, inventory,
                 │                  │  faction_standing, mission_log
                 │                  │
                 │  Retrieval       │  lore_chunks (vector + FTS),
                 │  Layer           │  scene_memories, summaries
                 └──────────────────┘
```

### Agent Responsibilities

| Agent | Model | Job | User-facing? |
|-------|-------|-----|:---:|
| **Orchestrator** | Gemini 2.5 Pro | Route, merge, consistency-check, apply player consequences | No |
| **Onboarding** | Gemini 2.5 Pro | Charon conducts check-in; builds player character | **Yes** (Charon's voice) |
| **Archivist** | Gemini 2.5 Flash | Lore, characters, rules, history | No |
| **Ledger** | Gemini 2.5 Flash | Debts, markers, reputation, relationships | No |
| **Timeline** | Gemini 2.5 Flash | Events, locations, collision detection | No |
| **Narrator** | Gemini 2.5 Pro | Cinematic prose — player is their character, Charon is NPC | **Yes** |

### Franchise Bible Architecture

The engine separates **narrative infrastructure** from **franchise content**. The orchestrator, ledger, timeline, consequence engine, MCP toolbox, and API layer are reusable across any IP. To deploy for a new franchise, update these files:

| Layer | Files | What Changes |
|-------|-------|-------------|
| **Lore & World** | `db/seed_lore.sql` | Characters, factions, locations, history, rules |
| **Voice & Tone** | `app/agents/*/prompt.md` | NPC personality, prose style, world-specific language |
| **Player Config** | `app/shared/types.py` | Archetypes, stat names, starting inventories |
| **Schema Labels** | `db/schema.sql` | Currency name, faction terminology |

Everything else — the multi-agent orchestration, consequence propagation, player state machine, mission loop, memory system, and database layer — stays the same.

#### Example: Swapping Franchises

| Concept | John Wick (current demo) | Sci-Fi Guild (hypothetical) | Fantasy Tavern (hypothetical) |
|---------|--------------------------|----------------------------|-------------------------------|
| **Hub location** | The Continental Hotel | Orbital Station Nexus-7 | The Hearthstone Inn |
| **Host NPC** | Charon (concierge) | ARIA (station AI) | Grimshaw (innkeeper) |
| **Currency** | Gold coins | Credits | Silver marks |
| **Player roles** | Assassin, Fixer, Cleaner... | Pilot, Engineer, Smuggler... | Ranger, Alchemist, Bard... |
| **Faction system** | High Table, Ruska Roma... | Corporations, Syndicates... | Guilds, Crowns, Covens... |
| **Rules** | No business on hotel grounds | Station neutrality pact | Hearthstone peace oath |

The prompts, seed data, and type definitions change. The engine does not.

See [`franchise/README.md`](franchise/README.md) for the full franchise-bible
spec and [`franchise/john-wick/manifest.md`](franchise/john-wick/manifest.md)
for a concrete list of the files that make up the demo franchise.

---

## The Player System

### Character Stats

| Stat | Range | Effect |
|------|-------|--------|
| `reputation` | 0–100 | Gates mission availability; affects how NPCs treat you |
| `combat_rating` | 0–100 | Referenced in physical confrontation scenes |
| `influence` | 0–100 | Determines access to restricted information and spaces |
| `gold_coins` | 0+ | Hotel currency — rooms, services, bribes, favors |

### Archetypes and Starting Inventory

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

### Reputation Thresholds

- **0–20**: Approaching excommunicado territory. The hotel's patience has limits.
- **21–50**: Known. Neutral standing. Charon is correct but not warm.
- **51–74**: Trusted Operative. Charon remembers your preferences.
- **75–89**: Senior Operative. Other guests make way. Management takes an interest.
- **90–100**: Legendary. The High Table knows your name. This is not always a good thing.

### The Mission Loop

```
Ask Charon for work
     ↓
Charon presents 1–3 available missions (filtered by reputation)
     ↓
Player accepts one
     ↓
World state shifts: Timeline tracks the mission, Ledger notes the obligation
     ↓
Player acts (multiple turns of free play)
     ↓
Player reports outcome to Charon
     ↓
complete_mission() applies: gold reward, reputation delta, consequences
     ↓
Charon acknowledges. The world has changed.
```

---

## Project Structure

```
continental-concierge/
├── app/
│   ├── agents/
│   │   ├── concierge/        # Orchestrator (root agent) — routing + player state
│   │   │   ├── agent.py
│   │   │   └── prompt.md
│   │   ├── onboarding/       # Charon conducts check-in (NEW)
│   │   │   ├── agent.py
│   │   │   └── prompt.md
│   │   ├── archivist/        # Lore & character retrieval
│   │   ├── ledger/           # Social graph accountant
│   │   ├── timeline/         # Events & collision detection
│   │   └── narrator/         # Cinematic prose — player is character, Charon is NPC
│   ├── tools/
│   │   ├── db.py             # AlloyDB connection pool (asyncpg) (NEW)
│   │   ├── player_tools.py   # Player CRUD: stats, missions, inventory, gold (NEW)
│   │   ├── world_state_tools.py
│   │   ├── lore_tools.py
│   │   ├── ledger_tools.py
│   │   ├── timeline_tools.py
│   │   └── consistency_tools.py
│   ├── shared/
│   │   ├── config.py
│   │   └── types.py          # PlayerCharacter, OnboardingState, MissionOffer + TaskTypes
│   └── server.py             # FastAPI: /chat, /player, /player/missions, /player/inventory
├── db/
│   ├── schema.sql            # Core world schema
│   ├── migrations/
│   │   └── 001_player_system.sql  # Player layer (NEW)
│   ├── seed_lore.sql
│   ├── retrieval_views.sql
│   └── seed_embeddings.py
├── franchise/                # Franchise bibles (the swappable layer)
│   ├── README.md             # How to fork for a new IP
│   └── john-wick/
│       └── manifest.md       # Files that constitute the demo franchise
├── mcp/
├── evals/                    # Engine correctness tests
│   └── README.md             # What each eval catches
├── infra/
│   ├── agent_engine/
│   ├── cloud_run/
│   └── terraform/
├── ui/
│   └── index.html           # Single-file demo client (served by FastAPI)
└── .github/
    └── workflows/
        └── ci.yml           # Lint + import smoke check on push / PR
```

---

## Setup & Deployment

### Prerequisites

- Google Cloud project with billing enabled
- `gcloud` CLI authenticated
- Terraform >= 1.5
- Python 3.12+

### Step 1: Provision Infrastructure

```bash
cd infra/terraform
export TF_VAR_project_id="your-project-id"
export TF_VAR_region="us-central1"
export TF_VAR_db_password="your-secure-password"
terraform init && terraform apply
```

### Step 2: Initialize Database

```bash
# Start AlloyDB Auth Proxy
alloydb-auth-proxy "projects/$PROJECT_ID/locations/$REGION/clusters/continental-cluster/instances/continental-primary"

# Run core schema, then player migration
psql -h 127.0.0.1 -U continental_app -d continental -f db/schema.sql
psql -h 127.0.0.1 -U continental_app -d continental -f db/migrations/001_player_system.sql
psql -h 127.0.0.1 -U continental_app -d continental -f db/seed_lore.sql
psql -h 127.0.0.1 -U continental_app -d continental -f db/retrieval_views.sql
```

### Step 3: Generate Embeddings

```bash
python db/seed_embeddings.py \
  --project $PROJECT_ID --region $REGION \
  --db-host 127.0.0.1 --db-password $DB_PASSWORD
```

### Step 4: Deploy MCP Server

```bash
cd infra/cloud_run
gcloud builds submit --tag $REGION-docker.pkg.dev/$PROJECT_ID/continental/mcp-server:latest ../../
gcloud run services replace service.yaml --region $REGION
```

### Step 5: Deploy Agents

```bash
python infra/agent_engine/deploy.py \
  --project $PROJECT_ID --region $REGION \
  --bucket gs://$PROJECT_ID-staging --test
```

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Liveness probe |
| `POST` | `/chat` | Main gameplay loop |
| `GET` | `/player/{session_id}` | Current player state |
| `GET` | `/player/{session_id}/missions` | Available missions |
| `GET` | `/player/{session_id}/inventory` | Inventory + gold balance |
| `GET` | `/world-state` | Day, phase, crisis level, hotel status |
| `GET` | `/characters` | Active NPC roster |
| `GET` | `/debts` | Outstanding debts and markers |
| `GET` | `/violations` | Pending rule violations |

### POST /chat

```json
{
  "message": "Ask Charon what work is available tonight.",
  "session_id": "user-abc-session-1",
  "user_id": "user-abc"
}
```

Response includes `player` snapshot for HUD rendering and `onboarding_complete` flag.

---

## Demo Walkthrough: First Night at the Continental

**Session start — Mystery path**

> *You push through the revolving door. The lobby is amber and leather and the particular quiet of people with business they don't discuss. A man behind the desk raises his eyes.*
>
> **Charon**: "Good evening. We've been expecting someone. I wasn't certain it would be you."
> *He consults the register.* "The name on the reservation is unclear. For now — how shall I address you?"

**Turn 2** — Player gives an alias. Charon notes it without comment. Asks where they've come from.

**Turn 3** — *"There is a sealed envelope for you. The sender noted an outstanding arrangement — weight of three. You're aware of this?"* The player's reaction seeds a faction relationship in the Ledger.

**Turn 5** — Identity crystallises from accumulated clues. The Archivist generates the backstory. Charon says the name aloud for the first time. *"Your suite is ready, [name]. The Continental is glad to have you back."*

**Onboarding complete. The world opens.**

---

**Turn 6** — *"Ask Charon what work is available."*

Charon slides a folded note across the desk without looking up. Three missions, filtered by reputation. The highest priority: *"A guest requires that a matter be concluded before the High Table convenes. Discreetly."*

**Turn 7** — Player accepts. Timeline records it. Ledger notes the obligation. The clock is running.

**Turn 12** — Player returns. Mission complete.

Charon: *"The matter is concluded, I take it."* He doesn't ask how. Gold changes hands. Reputation +15. The world notes it.

---

## Design Notes

### Charon is Not the Player

The most important architectural shift in v2: the player is an *operative* in the hotel, not the concierge running it. Charon is a fully realised NPC with his own voice, knowledge, and agenda. He is the player's primary interface to the world — mission-giver, information source, and the particular kind of ally who can only help you if you follow the rules.

### Two-Layer Character Model

Every player has two rows: `player_characters` (session state, stats, inventory, onboarding progress) and `characters` (the NPC-mirrored row created after onboarding completes). This makes the player visible to all existing Archivist / Ledger / Timeline queries — other characters can owe them debts, encounter them in the timeline, and reference them in lore.

### Consequence Propagation

Every significant player action triggers writes across multiple tables. Killing on hotel grounds creates a `rule_violations` row. Calling in a favor updates `debts_markers`. Completing a mission writes to `player_characters`, `missions`, `player_mission_log`, and optionally `events`. The world remembers everything.

### Memory Bank vs AlloyDB

| Memory Bank | AlloyDB |
|-------------|---------|
| User's narrative preferences | Who owes whom |
| Preferred faction / playstyle | What happened on day 4 |
| Tone calibration data | Which rules are active |
| Session continuity signals | Player's current gold balance |

### Session Persistence and Scale-to-Zero

**All gameplay state lives in AlloyDB, keyed by `session_id`.** The player
record — stats, inventory, onboarding progress, active mission, faction
standing — is written to `player_characters` and rehydrated at the top of
every turn. `server.py` injects `[session_id:xxx]` at the front of every
incoming message so the orchestrator can call `get_player(session_id)` as
its first step. Nothing that needs to survive a turn lives in agent memory.

**Where we are today (Phase 1):** the Agent Engine *session handle* itself
is still held in an in-process `_sessions` dict inside `server.py`. That
means a single Cloud Run instance can resume any client that hands it back
its `session_id`, but a full scale-to-zero restart will force the next
`/chat` to spin a fresh Agent Engine session. Gameplay state is still
intact — what gets recreated is the ADK session object, not the narrative.

**Where Phase 2 is going:** the `_sessions` dict gets replaced with an
AlloyDB-backed lookup so the Agent Engine session id is stored alongside
the player row. At that point every scale-to-zero transition is invisible
to the client and the same `session_id` is fully portable across browser
tabs, devices, or Cloud Run revisions. Tracked in `to-do-list.md` Phase 6.

The only state held in agent memory is the single-turn working context —
agent-to-agent hand-offs within one `/chat` call.
