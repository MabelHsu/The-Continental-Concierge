-- ============================================================================
-- THE CONTINENTAL CONCIERGE — AlloyDB Schema
-- ============================================================================
-- Two jobs: operational state (relational) + retrieval layer (vector/hybrid)
-- Requires: AlloyDB with google_ml_tfe and vector extensions enabled
-- ============================================================================

-- IMPORTANT: vector must be installed by a superuser BEFORE running this script.
-- On AlloyDB Omni (local dev), run this first:
--   PGPASSWORD=continental-dev psql -h localhost -U postgres -p 5432 -d continental \
--     -c "CREATE EXTENSION IF NOT EXISTS vector;"
-- On cloud AlloyDB, the extension is pre-installed — this line is a no-op.
CREATE EXTENSION IF NOT EXISTS vector;

-- google_ml_tfe enables the google_ml.embedding() SQL function in cloud AlloyDB.
-- It is NOT available in AlloyDB Omni (local dev) — and not needed, because
-- seed_embeddings.py generates vectors via the Python Vertex AI SDK instead.
-- This block silently skips the extension when running on Omni.
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_available_extensions WHERE name = 'google_ml_tfe'
    ) THEN
        CREATE EXTENSION IF NOT EXISTS google_ml_tfe;
    END IF;
END
$$;

-- ============================================================================
-- OPERATIONAL STATE
-- ============================================================================

-- World clock: singleton row tracking story progression
CREATE TABLE story_state (
    id              INTEGER PRIMARY KEY DEFAULT 1 CHECK (id = 1),
    current_day     INTEGER NOT NULL DEFAULT 1,
    current_phase   TEXT NOT NULL DEFAULT 'evening'
                    CHECK (current_phase IN ('morning','afternoon','evening','night','dawn')),
    crisis_level    INTEGER NOT NULL DEFAULT 1 CHECK (crisis_level BETWEEN 1 AND 10),
    crisis_name     TEXT NOT NULL DEFAULT 'The Calm Before',
    high_table_edict TEXT,
    hotel_status    TEXT NOT NULL DEFAULT 'open'
                    CHECK (hotel_status IN ('open','lockdown','compromised','sanctuary')),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE factions (
    id              SERIAL PRIMARY KEY,
    name            TEXT NOT NULL UNIQUE,
    type            TEXT NOT NULL DEFAULT 'syndicate'
                    CHECK (type IN ('syndicate','family','guild','independent','high_table','continental')),
    influence       INTEGER NOT NULL DEFAULT 50 CHECK (influence BETWEEN 0 AND 100),
    territory       TEXT,
    leader_id       INTEGER,
    status          TEXT NOT NULL DEFAULT 'active'
                    CHECK (status IN ('active','weakened','disbanded','underground','ascendant')),
    description     TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE locations (
    id              SERIAL PRIMARY KEY,
    name            TEXT NOT NULL,
    type            TEXT NOT NULL
                    CHECK (type IN ('hotel_room','hotel_common','hotel_service',
                                    'street','safehouse','territory','landmark','transit','unknown')),
    district        TEXT,
    is_continental  BOOLEAN NOT NULL DEFAULT false,
    is_neutral      BOOLEAN NOT NULL DEFAULT true,
    capacity        INTEGER,
    current_status  TEXT NOT NULL DEFAULT 'accessible'
                    CHECK (current_status IN ('accessible','restricted','compromised','destroyed','hidden')),
    description     TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE characters (
    id              SERIAL PRIMARY KEY,
    name            TEXT NOT NULL UNIQUE,
    alias           TEXT,
    title           TEXT,
    faction_id      INTEGER REFERENCES factions(id),
    status          TEXT NOT NULL DEFAULT 'active'
                    CHECK (status IN ('active','injured','hiding','excommunicado','dead','unknown')),
    reputation      INTEGER NOT NULL DEFAULT 50 CHECK (reputation BETWEEN 0 AND 100),
    traits          JSONB NOT NULL DEFAULT '[]',
    backstory       TEXT,
    current_location_id INTEGER REFERENCES locations(id),
    first_appeared_day  INTEGER NOT NULL DEFAULT 1,
    last_seen_day       INTEGER,
    last_seen_phase     TEXT,
    notes           TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE factions ADD CONSTRAINT fk_faction_leader FOREIGN KEY (leader_id) REFERENCES characters(id);

CREATE TABLE debts_markers (
    id              SERIAL PRIMARY KEY,
    creditor_id     INTEGER NOT NULL REFERENCES characters(id),
    debtor_id       INTEGER NOT NULL REFERENCES characters(id),
    marker_type     TEXT NOT NULL
                    CHECK (marker_type IN ('blood_oath','marker','favor','debt','promise','threat')),
    description     TEXT NOT NULL,
    value           INTEGER NOT NULL DEFAULT 1 CHECK (value BETWEEN 1 AND 10),
    status          TEXT NOT NULL DEFAULT 'outstanding'
                    CHECK (status IN ('outstanding','called_in','fulfilled','betrayed','expired','transferred')),
    origin_event_id INTEGER,
    called_in_day   INTEGER,
    fulfilled_day   INTEGER,
    witness_id      INTEGER REFERENCES characters(id),
    created_day     INTEGER NOT NULL DEFAULT 1,
    notes           TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE relationships (
    id              SERIAL PRIMARY KEY,
    character_a_id  INTEGER NOT NULL REFERENCES characters(id),
    character_b_id  INTEGER NOT NULL REFERENCES characters(id),
    type            TEXT NOT NULL
                    CHECK (type IN ('ally','rival','mentor','protege','enemy','neutral',
                                    'business','romantic','family','grudging_respect')),
    strength        INTEGER NOT NULL DEFAULT 50 CHECK (strength BETWEEN 0 AND 100),
    public_known    BOOLEAN NOT NULL DEFAULT true,
    origin_story    TEXT,
    last_interaction_day INTEGER,
    notes           TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(character_a_id, character_b_id)
);

CREATE TABLE events (
    id              SERIAL PRIMARY KEY,
    day             INTEGER NOT NULL,
    phase           TEXT NOT NULL
                    CHECK (phase IN ('morning','afternoon','evening','night','dawn')),
    event_type      TEXT NOT NULL
                    CHECK (event_type IN ('arrival','departure','meeting','conflict','transaction',
                                          'ceremony','violation','request','favor','assassination',
                                          'negotiation','betrayal','alliance','discovery','custom')),
    title           TEXT NOT NULL,
    description     TEXT NOT NULL,
    location_id     INTEGER REFERENCES locations(id),
    severity        INTEGER NOT NULL DEFAULT 3 CHECK (severity BETWEEN 1 AND 10),
    is_public       BOOLEAN NOT NULL DEFAULT true,
    is_resolved     BOOLEAN NOT NULL DEFAULT false,
    resolution      TEXT,
    consequences    JSONB DEFAULT '[]',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE event_participants (
    event_id        INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    character_id    INTEGER NOT NULL REFERENCES characters(id),
    role            TEXT NOT NULL DEFAULT 'participant'
                    CHECK (role IN ('instigator','participant','witness','victim','beneficiary','target')),
    PRIMARY KEY (event_id, character_id)
);

CREATE TABLE missions (
    id              SERIAL PRIMARY KEY,
    title           TEXT NOT NULL,
    requested_by_id INTEGER REFERENCES characters(id),
    assigned_to_id  INTEGER REFERENCES characters(id),
    mission_type    TEXT NOT NULL
                    CHECK (mission_type IN ('room_request','transport','favor','introduction',
                                            'etiquette_ruling','debt_settlement','rumor_check',
                                            'event_coordination','protection','assassination',
                                            'smuggling','negotiation','custom')),
    status          TEXT NOT NULL DEFAULT 'pending'
                    CHECK (status IN ('pending','active','completed','failed','cancelled','complicated')),
    priority        INTEGER NOT NULL DEFAULT 3 CHECK (priority BETWEEN 1 AND 5),
    description     TEXT NOT NULL,
    requirements    JSONB DEFAULT '{}',
    outcome         TEXT,
    deadline_day    INTEGER,
    deadline_phase  TEXT,
    created_day     INTEGER NOT NULL,
    created_phase   TEXT NOT NULL,
    completed_day   INTEGER,
    notes           TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE hotel_rules (
    id              SERIAL PRIMARY KEY,
    rule_number     INTEGER NOT NULL UNIQUE,
    title           TEXT NOT NULL,
    description     TEXT NOT NULL,
    penalty         TEXT NOT NULL,
    is_active       BOOLEAN NOT NULL DEFAULT true,
    exceptions      TEXT,
    added_day       INTEGER NOT NULL DEFAULT 0,
    source          TEXT NOT NULL DEFAULT 'founding_charter'
);

CREATE TABLE rule_violations (
    id              SERIAL PRIMARY KEY,
    rule_id         INTEGER NOT NULL REFERENCES hotel_rules(id),
    violator_id     INTEGER NOT NULL REFERENCES characters(id),
    event_id        INTEGER REFERENCES events(id),
    day             INTEGER NOT NULL,
    phase           TEXT NOT NULL,
    severity        TEXT NOT NULL DEFAULT 'minor'
                    CHECK (severity IN ('minor','moderate','severe','capital')),
    adjudication    TEXT
                    CHECK (adjudication IN ('pending','pardoned','punished','excommunicated','deferred')),
    punishment      TEXT,
    notes           TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE story_snapshots (
    id              SERIAL PRIMARY KEY,
    day             INTEGER NOT NULL,
    phase           TEXT NOT NULL,
    summary         TEXT NOT NULL,
    active_threads  JSONB NOT NULL DEFAULT '[]',
    tension_level   INTEGER NOT NULL CHECK (tension_level BETWEEN 1 AND 10),
    key_changes     JSONB NOT NULL DEFAULT '[]',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================================================
-- RETRIEVAL LAYER — Semantic + keyword hybrid search
-- ============================================================================

CREATE TABLE lore_chunks (
    id              SERIAL PRIMARY KEY,
    category        TEXT NOT NULL
                    CHECK (category IN ('history','rule','tradition','location_lore','character_lore',
                                        'faction_lore','artifact','ceremony','proverb','world_building')),
    title           TEXT NOT NULL,
    content         TEXT NOT NULL,
    tags            TEXT[] NOT NULL DEFAULT '{}',
    canon_level     TEXT NOT NULL DEFAULT 'established'
                    CHECK (canon_level IN ('established','rumored','legendary','classified')),
    embedding       vector(768),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE conversation_summaries (
    id              SERIAL PRIMARY KEY,
    session_id      TEXT NOT NULL,
    day             INTEGER NOT NULL,
    phase           TEXT NOT NULL,
    summary         TEXT NOT NULL,
    key_decisions   JSONB NOT NULL DEFAULT '[]',
    characters_involved INTEGER[] NOT NULL DEFAULT '{}',
    emotional_tone  TEXT,
    embedding       vector(768),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE scene_memories (
    id              SERIAL PRIMARY KEY,
    event_id        INTEGER REFERENCES events(id),
    day             INTEGER NOT NULL,
    phase           TEXT NOT NULL,
    scene_text      TEXT NOT NULL,
    location_id     INTEGER REFERENCES locations(id),
    mood            TEXT,
    significance    INTEGER NOT NULL DEFAULT 3 CHECK (significance BETWEEN 1 AND 10),
    tags            TEXT[] NOT NULL DEFAULT '{}',
    embedding       vector(768),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================================================
-- INDEXES
-- ============================================================================

CREATE INDEX idx_characters_faction ON characters(faction_id);
CREATE INDEX idx_characters_status ON characters(status);
CREATE INDEX idx_characters_location ON characters(current_location_id);
CREATE INDEX idx_debts_creditor ON debts_markers(creditor_id);
CREATE INDEX idx_debts_debtor ON debts_markers(debtor_id);
CREATE INDEX idx_debts_status ON debts_markers(status);
CREATE INDEX idx_events_day_phase ON events(day, phase);
CREATE INDEX idx_events_type ON events(event_type);
CREATE INDEX idx_events_location ON events(location_id);
CREATE INDEX idx_missions_status ON missions(status);
CREATE INDEX idx_relationships_chars ON relationships(character_a_id, character_b_id);
CREATE INDEX idx_violations_violator ON rule_violations(violator_id);
CREATE INDEX idx_characters_traits ON characters USING GIN(traits);
CREATE INDEX idx_events_consequences ON events USING GIN(consequences);

-- Vector indexes (HNSW at this scale; switch to ScaNN past ~100k rows)
CREATE INDEX idx_lore_embedding ON lore_chunks USING hnsw(embedding vector_cosine_ops) WITH (m=16, ef_construction=200);
CREATE INDEX idx_conversation_embedding ON conversation_summaries USING hnsw(embedding vector_cosine_ops) WITH (m=16, ef_construction=200);
CREATE INDEX idx_scene_embedding ON scene_memories USING hnsw(embedding vector_cosine_ops) WITH (m=16, ef_construction=200);
CREATE INDEX idx_lore_tags ON lore_chunks USING GIN(tags);
CREATE INDEX idx_scene_tags ON scene_memories USING GIN(tags);
