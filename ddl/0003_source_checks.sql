-- Verificações de saúde das fontes: disponibilidade, mudança de colunas e variação de volume.
CREATE SEQUENCE IF NOT EXISTS metadata.seq_source_checks;
CREATE TABLE IF NOT EXISTS metadata.source_checks (
    id BIGINT PRIMARY KEY DEFAULT nextval('metadata.seq_source_checks'),
    checked_at VARCHAR NOT NULL,
    source VARCHAR NOT NULL,
    dataset VARCHAR NOT NULL,
    partition INTEGER,
    check_name VARCHAR NOT NULL,
    status VARCHAR NOT NULL,
    detail VARCHAR
);
