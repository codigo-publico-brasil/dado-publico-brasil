-- Identidade de pessoas (ADR 0004): tabelas persistentes, que não se reconstroem do raw.
-- A chave da pessoa vem de uma sequência: nunca é reaproveitada, mesmo se a linha for apagada.
CREATE SCHEMA IF NOT EXISTS identity;
CREATE SEQUENCE IF NOT EXISTS identity.seq_pessoa;
CREATE TABLE IF NOT EXISTS identity.pessoa (
    id_pessoa BIGINT PRIMARY KEY DEFAULT nextval('identity.seq_pessoa'),
    created_at VARCHAR NOT NULL
);
CREATE TABLE IF NOT EXISTS identity.pessoa_identificador (
    source VARCHAR NOT NULL,
    id_type VARCHAR NOT NULL,
    source_id VARCHAR NOT NULL,
    id_pessoa BIGINT NOT NULL,
    method VARCHAR NOT NULL,
    confirmed_by VARCHAR NOT NULL,
    linked_at VARCHAR NOT NULL,
    PRIMARY KEY (source, id_type, source_id)
);
