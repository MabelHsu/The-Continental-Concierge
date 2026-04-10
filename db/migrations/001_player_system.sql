-- ============================================================================
-- MIGRATION 001: Player System
-- ============================================================================
-- Adds the player character layer on top of the world simulation.
-- Players are full characters in the world — their row in player_characters
-- is the source of truth for session state; their linked row in characters
-- participates in all existing Ledger / Timeline / Archivist queries.
-- ============================================================================

-- ── Player Characters ────────────────────────────────────────────────────────
-- One row per session. Persists across turns (AlloyDB, not ADK session memory).
-- After onboarding completes, a mirroring row is also inserted into `characters`
-- so the player participates in all NPC queries transparently.

CREATE TABLE player_characters (
    id                  SERIAL PRIMARY KEY,
    session_id          TEXT NOT NULL UNIQUE,    -- ties to server ChatRequest.session_id
    user_id             TEXT NOT NULL,

    -- Identity (populated during / after onboarding)
    name                TEXT,                    -- NULL on mystery path until revealed
    alias               TEXT,                    -- working name before full reveal
    title               TEXT,
    archetype           TEXT
                        CHECK (archetype IN (
                            'assassin', 'cleaner', 'fixer',
                            'information_broker', 'weapons_dealer',
                            'driver', 'medic', 'enforcer'
                        )),
    backstory           TEXT,

    -- Onboarding state
    creation_path       TEXT NOT NULL DEFAULT 'pending'
                        CHECK (creation_path IN ('pending', 'mystery', 'custom')),
    onboarding_complete BOOLEAN NOT NULL DEFAULT false,
    onboarding_step     INTEGER NOT NULL DEFAULT 0,
    -- mystery path accumulates clues here until identity crystallises
    identity_clues      JSONB NOT NULL DEFAULT '[]',
    identity_revealed   BOOLEAN NOT NULL DEFAULT false,

    -- Core stats (mirror of characters.reputation + extras)
    reputation          INTEGER NOT NULL DEFAULT 50 CHECK (reputation BETWEEN 0 AND 100),
    combat_rating       INTEGER NOT NULL DEFAULT 50 CHECK (combat_rating BETWEEN 0 AND 100),
    influence           INTEGER NOT NULL DEFAULT 30 CHECK (influence BETWEEN 0 AND 100),
    gold_coins          INTEGER NOT NULL DEFAULT 7,   -- starting: 7 gold coins

    -- World position
    faction_id          INTEGER REFERENCES factions(id),
    current_location_id INTEGER REFERENCES locations(id),
    status              TEXT NOT NULL DEFAULT 'active'
                        CHECK (status IN ('active', 'injured', 'hiding', 'excommunicado', 'dead')),

    -- Character link — set after onboarding completes
    character_id        INTEGER REFERENCES characters(id),

    -- Mission tracking
    active_mission_id   INTEGER,                  -- FK added below after missions table reference
    missions_completed  INTEGER NOT NULL DEFAULT 0,
    missions_failed     INTEGER NOT NULL DEFAULT 0,

    -- Audit
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Deferred FK: active_mission_id → missions
ALTER TABLE player_characters
    ADD CONSTRAINT fk_player_active_mission
    FOREIGN KEY (active_mission_id) REFERENCES missions(id)
    DEFERRABLE INITIALLY DEFERRED;


-- ── Player Inventory ─────────────────────────────────────────────────────────

CREATE TABLE player_inventory (
    id              SERIAL PRIMARY KEY,
    player_id       INTEGER NOT NULL REFERENCES player_characters(id) ON DELETE CASCADE,
    item_type       TEXT NOT NULL
                    CHECK (item_type IN (
                        'weapon', 'document', 'intel', 'vehicle',
                        'key', 'token', 'artifact', 'unknown'
                    )),
    name            TEXT NOT NULL,
    description     TEXT,
    quantity        INTEGER NOT NULL DEFAULT 1 CHECK (quantity >= 0),
    acquired_day    INTEGER NOT NULL DEFAULT 1,
    notes           TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);


-- ── Player Faction Standing ──────────────────────────────────────────────────
-- Separate from the global relationships table so player choices
-- don't pollute NPC social graph queries.

CREATE TABLE player_faction_standing (
    id              SERIAL PRIMARY KEY,
    player_id       INTEGER NOT NULL REFERENCES player_characters(id) ON DELETE CASCADE,
    faction_id      INTEGER NOT NULL REFERENCES factions(id),
    standing        INTEGER NOT NULL DEFAULT 50 CHECK (standing BETWEEN 0 AND 100),
    -- 0=open enemy, 50=neutral, 75=trusted, 90+=deep ally
    notes           TEXT,
    last_change_day INTEGER,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (player_id, faction_id)
);


-- ── Player Mission Log ───────────────────────────────────────────────────────
-- Tracks which missions the player has been offered, accepted, and how they resolved.

CREATE TABLE player_mission_log (
    id              SERIAL PRIMARY KEY,
    player_id       INTEGER NOT NULL REFERENCES player_characters(id) ON DELETE CASCADE,
    mission_id      INTEGER NOT NULL REFERENCES missions(id),
    offered_day     INTEGER NOT NULL,
    accepted_day    INTEGER,
    completed_day   INTEGER,
    outcome         TEXT CHECK (outcome IN ('success', 'failure', 'abandoned', 'complicated')),
    rewards_granted JSONB DEFAULT '{}',   -- {gold: 3, reputation_delta: +10, item: "..."}
    consequences    JSONB DEFAULT '[]',
    player_notes    TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);


-- ── Onboarding Conversation Log ──────────────────────────────────────────────
-- Stores each Charon exchange during character creation so it can be replayed
-- if the session dies mid-onboarding, and referenced by the Archivist when
-- generating the player's backstory on the mystery path.

CREATE TABLE onboarding_exchanges (
    id              SERIAL PRIMARY KEY,
    player_id       INTEGER NOT NULL REFERENCES player_characters(id) ON DELETE CASCADE,
    step            INTEGER NOT NULL,
    charon_line     TEXT NOT NULL,
    player_response TEXT,
    extracted_data  JSONB DEFAULT '{}',   -- structured data extracted from the response
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);


-- ── Indexes ──────────────────────────────────────────────────────────────────

CREATE INDEX idx_player_session ON player_characters(session_id);
CREATE INDEX idx_player_user ON player_characters(user_id);
CREATE INDEX idx_player_status ON player_characters(status);
CREATE INDEX idx_player_faction ON player_characters(faction_id);
CREATE INDEX idx_player_location ON player_characters(current_location_id);
CREATE INDEX idx_player_onboarding ON player_characters(onboarding_complete, creation_path);
CREATE INDEX idx_inventory_player ON player_inventory(player_id);
CREATE INDEX idx_inventory_type ON player_inventory(item_type);
CREATE INDEX idx_faction_standing_player ON player_faction_standing(player_id);
CREATE INDEX idx_mission_log_player ON player_mission_log(player_id);
CREATE INDEX idx_onboarding_player ON onboarding_exchanges(player_id, step);


-- ── Player Status View ───────────────────────────────────────────────────────
-- Flattened view used by all agents when they need the full player context.

CREATE OR REPLACE VIEW player_status_view AS
SELECT
    pc.id,
    pc.session_id,
    pc.user_id,
    pc.name,
    pc.alias,
    pc.title,
    pc.archetype,
    pc.backstory,
    pc.creation_path,
    pc.onboarding_complete,
    pc.onboarding_step,
    pc.identity_revealed,
    pc.identity_clues,
    pc.reputation,
    pc.combat_rating,
    pc.influence,
    pc.gold_coins,
    pc.status,
    pc.missions_completed,
    pc.missions_failed,
    -- Faction
    f.name                      AS faction_name,
    f.type                      AS faction_type,
    f.influence                 AS faction_influence,
    -- Location
    l.name                      AS current_location,
    l.type                      AS location_type,
    l.is_continental,
    -- Active mission
    m.title                     AS active_mission_title,
    m.mission_type              AS active_mission_type,
    m.deadline_day              AS mission_deadline_day,
    m.deadline_phase            AS mission_deadline_phase,
    m.priority                  AS mission_priority,
    -- Inventory summary
    (
        SELECT json_agg(json_build_object(
            'name', pi.name,
            'type', pi.item_type,
            'quantity', pi.quantity
        ))
        FROM player_inventory pi
        WHERE pi.player_id = pc.id
    )                           AS inventory,
    -- Faction standings summary
    (
        SELECT json_agg(json_build_object(
            'faction', pf_inner.name,
            'standing', pfs.standing
        ))
        FROM player_faction_standing pfs
        JOIN factions pf_inner ON pf_inner.id = pfs.faction_id
        WHERE pfs.player_id = pc.id
    )                           AS faction_standings,
    pc.created_at,
    pc.updated_at
FROM player_characters pc
LEFT JOIN factions f       ON f.id = pc.faction_id
LEFT JOIN locations l      ON l.id = pc.current_location_id
LEFT JOIN missions m       ON m.id = pc.active_mission_id;


-- ── Available Missions View ──────────────────────────────────────────────────
-- Used by the Concierge when offering work to the player.
-- Filters to unassigned, pending missions; reputation gate applied in application layer.

CREATE OR REPLACE VIEW available_missions_view AS
SELECT
    mi.id,
    mi.title,
    mi.mission_type,
    mi.description,
    mi.priority,
    mi.deadline_day,
    mi.deadline_phase,
    mi.requirements,
    c.name      AS requested_by,
    c.faction_id AS requester_faction_id,
    f.name      AS requester_faction,
    l.name      AS primary_location
FROM missions mi
LEFT JOIN characters c  ON c.id = mi.requested_by_id
LEFT JOIN factions f    ON f.id = c.faction_id
LEFT JOIN events e      ON e.id = (
    SELECT ep.event_id FROM event_participants ep WHERE ep.character_id = c.id
    ORDER BY ep.event_id DESC LIMIT 1
)
LEFT JOIN locations l   ON l.id = e.location_id
WHERE mi.status   = 'pending'
  AND mi.assigned_to_id IS NULL
ORDER BY mi.priority DESC, mi.created_at ASC;


-- ── Trigger: keep player updated_at fresh ───────────────────────────────────

CREATE OR REPLACE FUNCTION update_player_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_player_updated_at
    BEFORE UPDATE ON player_characters
    FOR EACH ROW EXECUTE FUNCTION update_player_updated_at();
