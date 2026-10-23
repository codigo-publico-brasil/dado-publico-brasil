#!/bin/sh
# Roda uma vez, na criação do volume: extensão de vetores, papel somente leitura e um banco só de testes.
set -e
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<SQL
CREATE EXTENSION IF NOT EXISTS vector;
CREATE ROLE leitor LOGIN PASSWORD '$LEITOR_PASSWORD';
GRANT CONNECT ON DATABASE $POSTGRES_DB TO leitor;
CREATE DATABASE teste;
SQL
