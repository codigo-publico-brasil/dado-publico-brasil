-- Metadados operacionais do pipeline (não são uma camada de dados).
CREATE SCHEMA IF NOT EXISTS metadata;
CREATE SEQUENCE IF NOT EXISTS metadata.seq_runs;
CREATE TABLE IF NOT EXISTS metadata.runs (
    id BIGINT PRIMARY KEY DEFAULT nextval('metadata.seq_runs'),
    stage VARCHAR NOT NULL,
    source VARCHAR,
    dataset VARCHAR,
    year INTEGER,
    started_at VARCHAR NOT NULL,
    finished_at VARCHAR,
    code_version VARCHAR,
    rows_in BIGINT,
    rows_out BIGINT,
    status VARCHAR NOT NULL,
    message VARCHAR
);
CREATE SEQUENCE IF NOT EXISTS metadata.seq_captures;
CREATE TABLE IF NOT EXISTS metadata.captures (
    id BIGINT PRIMARY KEY DEFAULT nextval('metadata.seq_captures'),
    source VARCHAR NOT NULL,
    dataset VARCHAR NOT NULL,
    year INTEGER,
    url VARCHAR NOT NULL,
    sha256 VARCHAR NOT NULL,
    size_bytes BIGINT NOT NULL,
    path VARCHAR NOT NULL,
    captured_at VARCHAR NOT NULL,
    last_checked_at VARCHAR NOT NULL,
    run_id BIGINT,
    etag VARCHAR,
    last_modified VARCHAR,
    loaded_at VARCHAR,
    UNIQUE (url, sha256)
);
CREATE TABLE IF NOT EXISTS metadata.dbt_results (
    run_id BIGINT,
    unique_id VARCHAR NOT NULL,
    kind VARCHAR NOT NULL,
    status VARCHAR NOT NULL,
    failures BIGINT,
    message VARCHAR,
    recorded_at VARCHAR NOT NULL
);
