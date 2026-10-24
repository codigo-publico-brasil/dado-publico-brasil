-- Observabilidade dos dados (ADR 0018): uma fotografia de cada tabela a cada execução e os achados da comparação
-- com a execução anterior (tabela que sumiu, volume que despencou ou explodiu, coluna nova ou removida, nulos que
-- aumentaram).
CREATE TABLE IF NOT EXISTS metadata.table_profile (
    run_id BIGINT NOT NULL,
    schema_name VARCHAR NOT NULL,
    table_name VARCHAR NOT NULL,
    row_count BIGINT NOT NULL,
    PRIMARY KEY (run_id, schema_name, table_name)
);
CREATE TABLE IF NOT EXISTS metadata.column_profile (
    run_id BIGINT NOT NULL,
    schema_name VARCHAR NOT NULL,
    table_name VARCHAR NOT NULL,
    column_name VARCHAR NOT NULL,
    data_type VARCHAR,
    null_rate DOUBLE,          -- só nos marts, o contrato com as aplicações
    distinct_values BIGINT,    -- só nos marts (contagem aproximada)
    PRIMARY KEY (run_id, schema_name, table_name, column_name)
);
CREATE SEQUENCE IF NOT EXISTS metadata.seq_data_checks;
CREATE TABLE IF NOT EXISTS metadata.data_checks (
    id BIGINT PRIMARY KEY DEFAULT nextval('metadata.seq_data_checks'),
    run_id BIGINT NOT NULL,
    checked_at VARCHAR NOT NULL,
    schema_name VARCHAR,
    table_name VARCHAR,
    column_name VARCHAR,
    check_name VARCHAR NOT NULL,
    status VARCHAR NOT NULL,   -- ok | warn | error
    detail VARCHAR
);
