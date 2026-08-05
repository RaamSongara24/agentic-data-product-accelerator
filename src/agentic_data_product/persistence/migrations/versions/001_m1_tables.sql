-- M1 application tables: runs, artefacts, audit, lineage

CREATE TABLE IF NOT EXISTS workflow_runs (
    run_id UUID PRIMARY KEY,
    status VARCHAR(64) NOT NULL DEFAULT 'created',
    title TEXT,
    created_by VARCHAR(256),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS artefacts (
    id SERIAL PRIMARY KEY,
    artefact_id UUID NOT NULL,
    run_id UUID NOT NULL REFERENCES workflow_runs (run_id) ON DELETE CASCADE,
    artefact_type VARCHAR(64) NOT NULL,
    version INTEGER NOT NULL CHECK (version >= 1),
    payload JSONB NOT NULL,
    created_by VARCHAR(256),
    governance_metadata JSONB,
    source_refs JSONB NOT NULL DEFAULT '[]'::jsonb,
    parent_versions JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_artefacts_run_type_version UNIQUE (run_id, artefact_type, version)
);

CREATE INDEX IF NOT EXISTS ix_artefacts_artefact_id ON artefacts (artefact_id);
CREATE INDEX IF NOT EXISTS ix_artefacts_run_id ON artefacts (run_id);

CREATE TABLE IF NOT EXISTS audit_events (
    event_id UUID PRIMARY KEY,
    run_id UUID NOT NULL REFERENCES workflow_runs (run_id) ON DELETE CASCADE,
    action VARCHAR(64) NOT NULL,
    entity_type VARCHAR(64) NOT NULL,
    entity_id VARCHAR(128) NOT NULL,
    details JSONB NOT NULL DEFAULT '{}'::jsonb,
    actor VARCHAR(256),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_audit_events_run_id ON audit_events (run_id);

CREATE TABLE IF NOT EXISTS lineage_edges (
    edge_id UUID PRIMARY KEY,
    run_id UUID NOT NULL REFERENCES workflow_runs (run_id) ON DELETE CASCADE,
    from_artefact_id UUID NOT NULL,
    from_version INTEGER NOT NULL CHECK (from_version >= 1),
    to_artefact_id UUID NOT NULL,
    to_version INTEGER NOT NULL CHECK (to_version >= 1),
    relationship VARCHAR(128) NOT NULL DEFAULT 'derived_from',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_lineage_edges_run_id ON lineage_edges (run_id);
