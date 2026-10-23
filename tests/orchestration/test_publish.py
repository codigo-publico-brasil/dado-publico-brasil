"""Publicação dos marts no PostgreSQL de serviço (ADR 0014). Precisa de um PostgreSQL de testes:
`docker compose up -d` e PLATAFORMA_TEST_POSTGRES apontando para o banco `teste` (nunca o de desenvolvimento,
que o teste sobrescreve). Sem a variável, os testes são pulados; o CI sobe o serviço."""

import os
from dataclasses import replace

import duckdb
import pytest

from plataforma_dados.core.settings import Settings
from plataforma_dados.core.warehouse import Connection, tables
from plataforma_dados.transformation import publish

DSN = os.environ.get("PLATAFORMA_TEST_POSTGRES")
needs_postgres = pytest.mark.skipif(not DSN, reason="PLATAFORMA_TEST_POSTGRES não definida")


@pytest.fixture
def service() -> duckdb.DuckDBPyConnection:
    """Conexão de conferência ao PostgreSQL; garante o papel `leitor` e deixa o banco limpo."""
    con = duckdb.connect()
    con.execute("INSTALL postgres")
    con.execute("LOAD postgres")
    con.execute(f"ATTACH '{DSN}' AS service (TYPE postgres)")
    con.execute(
        "CALL postgres_execute('service', \"DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'leitor') "
        "THEN CREATE ROLE leitor; END IF; END $$; DROP SCHEMA IF EXISTS marts CASCADE; "
        'DROP SCHEMA IF EXISTS marts_novo CASCADE")'
    )
    return con


def run(full: tuple[Connection, Settings]) -> dict[str, int]:
    con, settings = full
    con.close()  # o publish abre o arquivo do warehouse só para leitura
    return publish.publish(replace(settings, service_dsn=DSN))


def query(service: duckdb.DuckDBPyConnection, sql: str) -> list[tuple[object, ...]]:
    escaped = sql.replace("'", "''")
    return service.execute(f"SELECT * FROM postgres_query('service', '{escaped}')").fetchall()


@needs_postgres
def test_every_mart_is_published_with_the_same_number_of_rows(
    full: tuple[Connection, Settings], service: duckdb.DuckDBPyConnection
) -> None:
    con, settings = full
    expected = {t: con.execute(f"SELECT count(*) FROM marts.{t}").fetchone()[0] for t in tables(con, "marts")}  # type: ignore[index]
    assert run(full) == expected
    assert query(service, "SELECT count(*) FROM marts.pessoas") == [(expected["pessoas"],)]


@needs_postgres
def test_the_reader_role_can_select_and_nothing_stays_in_the_staging_schema(
    full: tuple[Connection, Settings], service: duckdb.DuckDBPyConnection
) -> None:
    run(full)
    assert query(service, "SELECT has_table_privilege('leitor', 'marts.pessoas', 'SELECT')") == [(True,)]
    assert query(service, "SELECT has_table_privilege('leitor', 'marts.pessoas', 'INSERT')") == [(False,)]
    assert query(
        service, "SELECT count(*) FROM information_schema.schemata WHERE schema_name = 'marts_novo'"
    ) == [(0,)]


@needs_postgres
def test_publishing_again_replaces_the_marts_without_duplicating_rows(
    full: tuple[Connection, Settings], service: duckdb.DuckDBPyConnection
) -> None:
    first = run(full)
    second = publish.publish(replace(full[1], service_dsn=DSN))
    assert first == second
    assert query(service, "SELECT count(*) FROM marts.pessoas") == [(first["pessoas"],)]


def test_publish_without_a_connection_string_explains_what_is_missing(settings: Settings) -> None:
    with pytest.raises(ValueError, match="PLATAFORMA_POSTGRES_DSN"):
        publish.publish(settings)
