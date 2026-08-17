CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE IF NOT EXISTS hydro_object (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    object_type TEXT NOT NULL,
    geometry geometry(Geometry, 4326) NOT NULL,
    properties JSONB NOT NULL DEFAULT '{}'::jsonb,
    source TEXT NOT NULL DEFAULT 'fixture',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_hydro_object_geometry
    ON hydro_object USING GIST (geometry);

CREATE INDEX IF NOT EXISTS idx_hydro_object_type
    ON hydro_object (object_type);

CREATE TABLE IF NOT EXISTS hydro_relation (
    id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL REFERENCES hydro_object(id) ON DELETE CASCADE,
    target_id TEXT NOT NULL REFERENCES hydro_object(id) ON DELETE CASCADE,
    relation_type TEXT NOT NULL,
    properties JSONB NOT NULL DEFAULT '{}'::jsonb,
    UNIQUE (source_id, target_id, relation_type)
);

CREATE INDEX IF NOT EXISTS idx_hydro_relation_source_type
    ON hydro_relation (source_id, relation_type);

CREATE INDEX IF NOT EXISTS idx_hydro_relation_target_type
    ON hydro_relation (target_id, relation_type);

CREATE TABLE IF NOT EXISTS scenario (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    mode TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS hydro_state (
    scenario_id TEXT NOT NULL REFERENCES scenario(id) ON DELETE CASCADE,
    object_id TEXT NOT NULL REFERENCES hydro_object(id) ON DELETE CASCADE,
    timestamp_minutes INTEGER NOT NULL,
    variable TEXT NOT NULL,
    value DOUBLE PRECISION NOT NULL,
    unit TEXT NOT NULL,
    PRIMARY KEY (scenario_id, object_id, timestamp_minutes, variable)
);
