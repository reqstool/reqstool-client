# Copyright © LFV

SCHEMA_DDL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS requirements (
    urn TEXT NOT NULL,
    id TEXT NOT NULL,
    title TEXT NOT NULL,
    significance TEXT NOT NULL CHECK (significance IN ('shall', 'should', 'may')),
    lifecycle_state TEXT NOT NULL CHECK (lifecycle_state IN ('draft', 'effective', 'deprecated', 'obsolete')),
    lifecycle_reason TEXT,
    implementation TEXT NOT NULL CHECK (implementation IN ('in-code', 'N/A')),
    description TEXT NOT NULL,
    rationale TEXT,
    revision TEXT NOT NULL,
    PRIMARY KEY (urn, id)
);

CREATE TABLE IF NOT EXISTS requirement_categories (
    req_urn TEXT NOT NULL,
    req_id TEXT NOT NULL,
    category TEXT NOT NULL CHECK (category IN (
        'functional-suitability', 'performance-efficiency', 'compatibility',
        'interaction-capability', 'reliability', 'security',
        'maintainability', 'flexibility', 'safety'
    )),
    PRIMARY KEY (req_urn, req_id, category),
    FOREIGN KEY (req_urn, req_id) REFERENCES requirements (urn, id) ON DELETE CASCADE
);

-- No FK on (ref_req_urn, ref_req_id) because references may point to external URNs not in the database
CREATE TABLE IF NOT EXISTS requirement_references (
    req_urn TEXT NOT NULL,
    req_id TEXT NOT NULL,
    ref_req_urn TEXT NOT NULL,
    ref_req_id TEXT NOT NULL,
    PRIMARY KEY (req_urn, req_id, ref_req_urn, ref_req_id),
    FOREIGN KEY (req_urn, req_id) REFERENCES requirements (urn, id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS svcs (
    urn TEXT NOT NULL,
    id TEXT NOT NULL,
    title TEXT NOT NULL,
    verification_type TEXT NOT NULL CHECK (verification_type IN (
        'automated-test', 'manual-test', 'review', 'platform', 'other'
    )),
    lifecycle_state TEXT NOT NULL CHECK (lifecycle_state IN ('draft', 'effective', 'deprecated', 'obsolete')),
    lifecycle_reason TEXT,
    description TEXT,
    instructions TEXT,
    revision TEXT NOT NULL,
    PRIMARY KEY (urn, id)
);

CREATE TABLE IF NOT EXISTS svc_requirement_links (
    svc_urn TEXT NOT NULL,
    svc_id TEXT NOT NULL,
    req_urn TEXT NOT NULL,
    req_id TEXT NOT NULL,
    PRIMARY KEY (svc_urn, svc_id, req_urn, req_id),
    FOREIGN KEY (svc_urn, svc_id) REFERENCES svcs (urn, id) ON DELETE CASCADE,
    FOREIGN KEY (req_urn, req_id) REFERENCES requirements (urn, id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS mvrs (
    urn TEXT NOT NULL,
    id TEXT NOT NULL,
    passed INTEGER NOT NULL,
    comment TEXT,
    PRIMARY KEY (urn, id)
);

CREATE TABLE IF NOT EXISTS mvr_svc_links (
    mvr_urn TEXT NOT NULL,
    mvr_id TEXT NOT NULL,
    svc_urn TEXT NOT NULL,
    svc_id TEXT NOT NULL,
    PRIMARY KEY (mvr_urn, mvr_id, svc_urn, svc_id),
    FOREIGN KEY (mvr_urn, mvr_id) REFERENCES mvrs (urn, id) ON DELETE CASCADE,
    FOREIGN KEY (svc_urn, svc_id) REFERENCES svcs (urn, id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS annotations_impls (
    req_urn TEXT NOT NULL,
    req_id TEXT NOT NULL,
    element_kind TEXT NOT NULL CHECK (element_kind IN (
        'FIELD', 'METHOD', 'CLASS', 'ENUM', 'INTERFACE', 'RECORD'
    )),
    fqn TEXT NOT NULL,
    PRIMARY KEY (req_urn, req_id, element_kind, fqn),
    FOREIGN KEY (req_urn, req_id) REFERENCES requirements (urn, id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS annotations_tests (
    svc_urn TEXT NOT NULL,
    svc_id TEXT NOT NULL,
    element_kind TEXT NOT NULL CHECK (element_kind IN (
        'FIELD', 'METHOD', 'CLASS', 'ENUM', 'INTERFACE', 'RECORD'
    )),
    fqn TEXT NOT NULL,
    PRIMARY KEY (svc_urn, svc_id, element_kind, fqn),
    FOREIGN KEY (svc_urn, svc_id) REFERENCES svcs (urn, id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS test_results (
    urn TEXT NOT NULL,
    fqn TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('passed', 'failed', 'skipped', 'missing')),
    PRIMARY KEY (urn, fqn)
);

CREATE TABLE IF NOT EXISTS parsing_graph (
    parent_urn TEXT NOT NULL,
    child_urn TEXT NOT NULL,
    PRIMARY KEY (parent_urn, child_urn)
);

CREATE TABLE IF NOT EXISTS urn_metadata (
    urn TEXT NOT NULL PRIMARY KEY,
    variant TEXT NOT NULL CHECK (variant IN ('system', 'microservice', 'external')),
    title TEXT NOT NULL,
    url TEXT,
    parse_position INTEGER NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS metadata (
    key TEXT NOT NULL PRIMARY KEY,
    value TEXT
);

-- FK indexes
CREATE INDEX IF NOT EXISTS idx_req_categories_fk ON requirement_categories (req_urn, req_id);
CREATE INDEX IF NOT EXISTS idx_req_references_fk ON requirement_references (req_urn, req_id);
CREATE INDEX IF NOT EXISTS idx_svc_req_links_svc ON svc_requirement_links (svc_urn, svc_id);
CREATE INDEX IF NOT EXISTS idx_svc_req_links_req ON svc_requirement_links (req_urn, req_id);
CREATE INDEX IF NOT EXISTS idx_mvr_svc_links_mvr ON mvr_svc_links (mvr_urn, mvr_id);
CREATE INDEX IF NOT EXISTS idx_mvr_svc_links_svc ON mvr_svc_links (svc_urn, svc_id);
CREATE INDEX IF NOT EXISTS idx_annotations_impls_fk ON annotations_impls (req_urn, req_id);
CREATE INDEX IF NOT EXISTS idx_annotations_tests_fk ON annotations_tests (svc_urn, svc_id);
CREATE INDEX IF NOT EXISTS idx_parsing_graph_parent ON parsing_graph (parent_urn);
CREATE INDEX IF NOT EXISTS idx_parsing_graph_child ON parsing_graph (child_urn);
"""
