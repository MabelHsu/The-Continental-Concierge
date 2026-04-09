# The Continental Concierge

A multi-agent narrative system where you play the concierge desk for a fictional hotel under crisis. Characters ask for rooms, transport, favors, etiquette rulings, introductions, debt settlements, rumor checks, and event coordination. The system tracks loyalties, debts, hotel rules, location timelines, and evolving story state.

Built on the Google Cloud stack: **ADK** (Agent Development Kit), **Vertex AI Agent Engine**, **AlloyDB**, **Cloud Run**, and **MCP Toolbox for Databases**.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     Player (You)                        │
│              "Sofia wants a room. Handle it."           │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────┐
│              Concierge Orchestrator                      │
│         (Vertex AI Agent Engine / Gemini 2.5 Pro)        │
│                                                          │
│  1. Understands the request                              │
│  2. Routes to specialists                                │
│  3. Merges structured outputs                            │
│  4. Runs Canon Judge consistency check                   │
│  5. Delivers final response                              │
└──────────┬──────────┬──────────┬──────────┬──────────────┘
           │          │          │          │
           ▼          ▼          ▼          ▼
      ┌─────────┐┌────────┐ ┌────────┐┌──────────┐
      │Archivist││ Ledger │ │Timeline││ Narrator │
      │  Agent  ││ Agent  │ │ Agent  ││  Agent   │
      │(Flash)  ││(Flash) │ │(Flash) ││  (Pro)   │
      └──┬──────┘└──┬─────┘ └──┬─────┘└───┬──────┘
         │          │          │          │
         └──────────┴──────────┴──────────┘
                    │
        ┌───────────┴───────────┐
        ▼                       ▼
┌──────────────┐    ┌───────────────────┐
│  MCP Toolbox │    │ Custom World MCP  │
│  (Read-only) │    │ (Write operations)│
│              │    │   (Cloud Run)     │
└──────┬───────┘    └────────┬──────────┘
       │                     │
       └──────────┬──────────┘
                  ▼
        ┌──────────────────┐
        │     AlloyDB      │
        │                  │
        │ ┌──────────────┐ │
        │ │  Operational │ │  characters, factions, debts,
        │ │    State     │ │  events, missions, rules
        │ └──────────────┘ │
        │ ┌──────────────┐ │
        │ │  Retrieval   │ │  lore_chunks (vector + FTS),
        │ │    Layer     │ │  scene_memories, summaries
        │ └──────────────┘ │
        └──────────────────┘
```

### Agent Responsibilities

| Agent | Model | Job | Returns |
|-------|-------|-----|---------|
| **Orchestrator** | Gemini 2.5 Pro | Route, merge, consistency-check | Final response to player |
| **Archivist** | Gemini 2.5 Flash | Lore, characters, rules, history | Structured JSON |
| **Ledger** | Gemini 2.5 Flash | Debts, markers, reputation, violations | Structured JSON |
| **Timeline** | Gemini 2.5 Flash | Events, locations, collision detection | Structured JSON |
| **Narrator** | Gemini 2.5 Pro | Cinematic prose from structured data | User-facing text |

### Control Model

- The Orchestrator decides the plan. Specialists never call each other.
- Specialists return structured data, not prose.
- The Narrator is the **only** agent that writes user-facing text.
- The Canon Judge (consistency check) runs before every final response.

---

## Project Structure

```
continental-concierge/
├── app/
│   ├── agents/
│   │   ├── concierge/        # Orchestrator (root agent)
│   │   │   ├── agent.py
│   │   │   └── prompt.md
│   │   ├── archivist/        # Lore & character retrieval
│   │   │   ├── agent.py
│   │   │   └── prompt.md
│   │   ├── ledger/           # Social graph accountant
│   │   │   ├── agent.py
│   │   │   └── prompt.md
│   │   ├── timeline/         # Events & collision detection
│   │   │   ├── agent.py
│   │   │   └── prompt.md
│   │   └── narrator/         # Cinematic prose output
│   │       ├── agent.py
│   │       └── prompt.md
│   ├── tools/
│   │   ├── db.py             # AlloyDB connection pooling
│   │   ├── world_state_tools.py
│   │   ├── lore_tools.py     # Hybrid search, dossiers
│   │   ├── ledger_tools.py   # Debt CRUD, reputation
│   │   ├── timeline_tools.py # Event scheduling, moves
│   │   └── consistency_tools.py  # Canon Judge
│   └── server.py             # FastAPI for Cloud Run
├── mcp/
│   ├── custom_world_mcp/     # Write-operation MCP server
│   │   └── server.py
│   └── alloydb_toolbox_config/
│       └── tools.yaml        # MCP Toolbox for Databases config
├── db/
│   ├── schema.sql            # Full AlloyDB schema
│   ├── seed_lore.sql         # Characters, factions, locations, rules, lore
│   ├── retrieval_views.sql   # Pre-built views for each agent
│   └── seed_embeddings.py    # Generate Vertex AI embeddings
├── evals/
│   ├── continuity_eval.py    # Character persistence across turns
│   ├── contradiction_eval.py # Detects impossible states
│   ├── memory_retrieval_eval.py  # Hybrid search quality
│   └── agent_routing_eval.py # Orchestrator routes correctly
├── infra/
│   ├── agent_engine/
│   │   └── deploy.py         # Deploy to Vertex AI Agent Engine
│   ├── cloud_run/
│   │   ├── Dockerfile
│   │   └── service.yaml
│   └── terraform/
│       └── main.tf           # AlloyDB, Cloud Run, IAM, VPC
├── ui/                        # (optional) Frontend
├── requirements.txt
└── README.md
```

---

## How AlloyDB Is Used (Two Jobs)

### Job 1: Operational State (Relational)

| Table | Purpose |
|-------|---------|
| `characters` | Every NPC — name, faction, reputation (0–100), traits, current location |
| `factions` | High Table, syndicates, hotel network — influence scores, territories |
| `locations` | Hotels, safe houses, clubs — consecration status, capacity |
| `debts_markers` | Blood oaths, gold coins, favors — creditor/debtor with weight 1–10 |
| `relationships` | Directed social graph — ally/rival/enemy with strength 0–100 |
| `events` | Everything that happens — day, time, location, participants, outcome |
| `missions` | Multi-step tasks with deadlines and rewards |
| `hotel_rules` | The 10 rules with severity levels and active/inactive status |
| `rule_violations` | Tracked separately with pending/adjudicated status |
| `story_snapshots` | Periodic world-state captures for rollback |

### Job 2: Retrieval Layer (Embeddings + Hybrid Search)

| Table | Purpose |
|-------|---------|
| `lore_chunks` | Canonical world-building with `vector(768)` embeddings + full-text search |
| `conversation_summaries` | Compressed session memory with embeddings |
| `scene_memories` | Rendered narrative scenes for Narrator callbacks |

The `hybrid_lore_search()` function combines vector similarity and keyword search using **Reciprocal Rank Fusion (RRF)** — because "John owes Sofia a marker from the Casablanca incident" is partly structured, partly semantic.

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

# Set your variables
export TF_VAR_project_id="your-project-id"
export TF_VAR_region="us-central1"
export TF_VAR_db_password="your-secure-password"

terraform init
terraform plan
terraform apply
```

This creates: AlloyDB cluster + instance, VPC, Cloud Run service, Artifact Registry, Secret Manager secrets, IAM bindings.

### Step 2: Initialize Database

Connect to AlloyDB (via Auth Proxy or Cloud Shell):

```bash
# Start AlloyDB Auth Proxy
alloydb-auth-proxy "projects/$PROJECT_ID/locations/$REGION/clusters/continental-cluster/instances/continental-primary"

# In another terminal
psql -h 127.0.0.1 -U continental_app -d continental

# Run schema, seed data, and views
\i db/schema.sql
\i db/seed_lore.sql
\i db/retrieval_views.sql
```

### Step 3: Generate Embeddings

```bash
python db/seed_embeddings.py \
  --project $PROJECT_ID \
  --region $REGION \
  --db-host 127.0.0.1 \
  --db-password $DB_PASSWORD
```

### Step 4: Deploy MCP Server to Cloud Run

```bash
# Build and push
cd infra/cloud_run
gcloud builds submit --tag $REGION-docker.pkg.dev/$PROJECT_ID/continental/mcp-server:latest ../../

# Deploy
gcloud run services replace service.yaml \
  --region $REGION \
  --set-env-vars "PROJECT_ID=$PROJECT_ID,REGION=$REGION"
```

### Step 5: Deploy Agents to Agent Engine

```bash
python infra/agent_engine/deploy.py \
  --project $PROJECT_ID \
  --region $REGION \
  --bucket gs://$PROJECT_ID-staging \
  --test
```

### Step 6: Run Evals

```bash
# Database-level evals (need AlloyDB connection)
python -m evals.continuity_eval
python -m evals.contradiction_eval
python -m evals.memory_retrieval_eval

# Agent-level eval (needs deployed Agent Engine)
python -m evals.agent_routing_eval \
  --agent-id $AGENT_ENGINE_ID \
  --project $PROJECT_ID
```

---

## Demo Walkthrough: A Night at the Continental

Here's what a 10-turn demo session looks like:

**Turn 1** — *"What's the situation?"*
→ Timeline reports: Day 1 morning. The Adjudicator has arrived. Sofia is requesting a room. Tension is high.

**Turn 2** — *"Give Sofia a suite on the 12th floor. Park view."*
→ Ledger notes: Sofia owes Winston a weight-7 favor. Timeline: Sofia moved to Continental NY. Narrator renders the check-in scene — dogs and all.

**Turn 3** — *"The Adjudicator wants to see the guest register."*
→ Archivist pulls the Adjudicator's dossier (reputation 95, role: adjudicator). Timeline lists all current guests. Narrator plays the tension of handing over the register.

**Turn 4** — *"Advance to evening. What's happening?"*
→ Timeline advances. Reports: Cassian is at the Red Circle. The Bowery King's people have been spotted near the hotel.

**Turn 5** — *"Sofia asks me to arrange a meeting with Cassian. Neutral ground."*
→ Archivist: their history (rival, Camorra friction). Ledger: Cassian owes Koji a service debt. Timeline: schedules meeting at Tarkovsky Theater (neutral). Narrator renders Sofia's request scene.

**Turn 6** — *"Someone just fired a shot in the lobby."*
→ Consistency check: Continental is consecrated ground → Rule 1 violation → capital offense. Ledger records the violation (pending adjudication). Narrator renders the chaos.

**Turn 7** — *"The Adjudicator wants to know who did it."*
→ Archivist: who was in the lobby? Timeline: checks lobby events. Narrator plays the interrogation.

**Turn 8** — *"Call in Sofia's marker. Winston needs her help."*
→ Ledger: resolves the weight-7 favor. Sofia's debt to Winston is now fulfilled. Reputation shifts. Narrator renders the tense exchange.

**Turn 9** — *"The Bowery King requests a meeting with Winston. Top of the hotel. Midnight."*
→ Timeline: schedules it, checks conflicts (enemies at same location warning). Archivist: their relationship (rival, strength 45). Narrator sets the rooftop scene.

**Turn 10** — *"Advance to night. Let the meeting play out."*
→ All agents coordinated. Timeline advances. Narrator delivers the climactic rooftop scene with full context — debts, history, the shooting, the Adjudicator's presence below.

---

## Memory Bank vs AlloyDB

| Memory Bank | AlloyDB |
|-------------|---------|
| "This user prefers political intrigue" | "Who owes whom" |
| "User hates retcons" | "What happened on day 4" |
| "User likes the Osaka setting" | "Which hotel rules are active" |
| User-specific preferences | Canonical world state |

Memory Bank handles personalization. AlloyDB is the source of truth for the world.
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      