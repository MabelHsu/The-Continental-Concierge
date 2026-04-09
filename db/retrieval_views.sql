-- ============================================================================
-- RETRIEVAL VIEWS — Prebuilt queries the agents use most often
-- ============================================================================

-- Full character dossier with faction and location
CREATE OR REPLACE VIEW v_character_dossier AS
SELECT
    c.id, c.name, c.alias, c.title, c.status, c.reputation, c.traits,
    c.backstory, c.notes, c.first_appeared_day, c.last_seen_day, c.last_seen_phase,
    f.name AS faction_name, f.type AS faction_type,
    l.name AS location_name, l.type AS location_type, l.district
FROM characters c
LEFT JOIN factions f ON c.faction_id = f.id
LEFT JOIN locations l ON c.current_location_id = l.id;

-- All outstanding debts with character names
CREATE OR REPLACE VIEW v_active_debts AS
SELECT
    d.id, d.marker_type, d.description, d.value, d.status,
    d.created_day, d.called_in_day, d.notes,
    cr.name AS creditor_name, cr.alias AS creditor_alias,
    db.name AS debtor_name, db.alias AS debtor_alias,
    w.name AS witness_name
FROM debts_markers d
JOIN characters cr ON d.creditor_id = cr.id
JOIN characters db ON d.debtor_id = db.id
LEFT JOIN characters w ON d.witness_id = w.id
WHERE d.status IN ('outstanding', 'called_in');

-- Current scene: who is where right now
CREATE OR REPLACE VIEW v_current_scene AS
SELECT
    l.id AS location_id, l.name AS location_name, l.type AS location_type,
    l.district, l.is_continental, l.current_status,
    json_agg(json_build_object(
        'character_id', c.id,
        'name', c.name,
        'alias', c.alias,
        'status', c.status,
        'faction', f.name
    )) FILTER (WHERE c.id IS NOT NULL) AS characters_present
FROM locations l
LEFT JOIN characters c ON c.current_location_id = l.id AND c.status = 'active'
LEFT JOIN factions f ON c.faction_id = f.id
GROUP BY l.id, l.name, l.type, l.district, l.is_continental, l.current_status;

-- Pending missions
CREATE OR REPLACE VIEW v_pending_missions AS
SELECT
    m.id, m.title, m.mission_type, m.status, m.priority, m.description,
    m.requirements, m.deadline_day, m.deadline_phase, m.notes,
    req.name AS requested_by, asgn.name AS assigned_to
FROM missions m
LEFT JOIN characters req ON m.requested_by_id = req.id
LEFT JOIN characters asgn ON m.assigned_to_id = asgn.id
WHERE m.status IN ('pending', 'active')
ORDER BY m.priority DESC, m.created_at;

-- Timeline view: recent events with participants
CREATE OR REPLACE VIEW v_timeline AS
SELECT
    e.id, e.day, e.phase, e.event_type, e.title, e.description,
    e.severity, e.is_public, e.is_resolved, e.resolution,
    l.name AS location_name,
    json_agg(json_build_object(
        'name', c.name, 'role', ep.role
    )) FILTER (WHERE c.id IS NOT NULL) AS participants
FROM events e
LEFT JOIN locations l ON e.location_id = l.id
LEFT JOIN event_participants ep ON e.id = ep.event_id
LEFT JOIN characters c ON ep.character_id = c.id
GROUP BY e.id, e.day, e.phase, e.event_type, e.title, e.description,
         e.severity, e.is_public, e.is_resolved, e.resolution, l.name
ORDER BY e.day DESC, 
    CASE e.phase WHEN 'dawn' THEN 1 WHEN 'morning' THEN 2 WHEN 'afternoon' THEN 3 
                 WHEN 'evening' THEN 4 WHEN 'night' THEN 5 END DESC;

-- Social graph: all relationships with names
CREATE OR REPLACE VIEW v_social_graph AS
SELECT
    r.id, r.type, r.strength, r.public_known, r.origin_story, r.notes,
    a.name AS character_a, a.alias AS alias_a,
    b.name AS character_b, b.alias AS alias_b
FROM relationships r
JOIN characters a ON r.character_a_id = a.id
JOIN characters b ON r.character_b_id = b.id;

-- Rule violations pending adjudication
CREATE OR REPLACE VIEW v_pending_violations AS
SELECT
    rv.id, rv.day, rv.phase, rv.severity, rv.adjudication, rv.notes,
    hr.rule_number, hr.title AS rule_title, hr.penalty AS rule_penalty,
    c.name AS violator_name
FROM rule_violations rv
JOIN hotel_rules hr ON rv.rule_id = hr.id
JOIN characters c ON rv.violator_id = c.id
WHERE rv.adjudication = 'pending';

-- ============================================================================
-- HYBRID SEARCH FUNCTION
-- Uses AlloyDB's hybrid_search with reciprocal rank fusion
-- ============================================================================

-- Semantic + keyword search over lore
CREATE OR REPLACE FUNCTION search_lore(
    query_text TEXT,
    query_embedding vector(768),
    result_limit INTEGER DEFAULT 5
)
RETURNS TABLE (
    id INTEGER,
    title TEXT,
    content TEXT,
    category TEXT,
    canon_level TEXT,
    tags TEXT[],
    relevance_score FLOAT
) AS $$
    SELECT
        lc.id, lc.title, lc.content, lc.category, lc.canon_level, lc.tags,
        -- Reciprocal rank fusion: combine vector similarity + tag overlap
        (1.0 / (1 + rank() OVER (ORDER BY lc.embedding <=> query_embedding)))
        +
        (CASE WHEN lc.tags && string_to_array(query_text, ' ') THEN 0.3 ELSE 0.0 END)
        AS relevance_score
    FROM lore_chunks lc
    ORDER BY lc.embedding <=> query_embedding
    LIMIT result_limit;
$$ LANGUAGE SQL STABLE;

-- Semantic search over scene memories
CREATE OR REPLACE FUNCTION search_scenes(
    query_embedding vector(768),
    day_from INTEGER DEFAULT NULL,
    day_to INTEGER DEFAULT NULL,
    result_limit INTEGER DEFAULT 5
)
RETURNS TABLE (
    id INTEGER,
    day INTEGER,
    phase TEXT,
    scene_text TEXT,
    mood TEXT,
    significance INTEGER,
    tags TEXT[],
    similarity FLOAT
) AS $$
    SELECT
        sm.id, sm.day, sm.phase, sm.scene_text, sm.mood, sm.significance, sm.tags,
        1 - (sm.embedding <=> query_embedding) AS similarity
    FROM scene_memories sm
    WHERE (day_from IS NULL OR sm.day >= day_from)
      AND (day_to IS NULL OR sm.day <= day_to)
    ORDER BY sm.embedding <=> query_embedding
    LIMIT result_limit;
$$ LANGUAGE SQL STABLE;
