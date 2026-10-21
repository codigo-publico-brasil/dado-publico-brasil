-- Cada resposta de um dataset por item (`foreach`): o que a fonte respondeu para cada item, com o hash do
-- corpo. Os corpos ficam byte a byte nos lotes do landing; esta tabela é o índice para auditar e retomar.
CREATE SEQUENCE IF NOT EXISTS metadata.seq_capture_items;
CREATE TABLE IF NOT EXISTS metadata.capture_items (
    id BIGINT PRIMARY KEY DEFAULT nextval('metadata.seq_capture_items'),
    capture_id BIGINT NOT NULL,
    source VARCHAR NOT NULL,
    dataset VARCHAR NOT NULL,
    item VARCHAR NOT NULL,
    url VARCHAR NOT NULL,
    status INTEGER NOT NULL,
    sha256 VARCHAR NOT NULL,
    fetched_at VARCHAR NOT NULL,
    version VARCHAR
);
