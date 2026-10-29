"""Publicação dos marts no PostgreSQL de serviço (ADR 0014). Precisa de um PostgreSQL de testes:
`docker compose up -d` e DADO_PUBLICO_TEST_POSTGRES apontando para o banco `teste` (nunca o de desenvolvimento,
que o teste sobrescreve). Sem a variável, os testes são pulados; o CI sobe o serviço."""

import os
from dataclasses import replace
from pathlib import Path

import duckdb
import pytest

from dado_publico_brasil.core.settings import Settings
from dado_publico_brasil.core.warehouse import Connection, scalar, tables
from dado_publico_brasil.transformation import publish

DSN = os.environ.get("DADO_PUBLICO_TEST_POSTGRES")
needs_postgres = pytest.mark.skipif(not DSN, reason="DADO_PUBLICO_TEST_POSTGRES não definida")


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


def expected_rows(con: Connection) -> dict[str, int]:
    """O que o publish deve devolver: as tabelas e views dos marts, com as linhas de cada uma."""
    return {t: int(scalar(con, f"SELECT count(*) FROM marts.{t}")) for t in tables(con, "marts")}


@needs_postgres
def test_every_mart_is_published_with_the_same_number_of_rows(
    full: tuple[Connection, Settings], service: duckdb.DuckDBPyConnection
) -> None:
    con, settings = full
    expected = expected_rows(con)
    assert any(name.startswith("app_") for name in expected)
    assert run(full) == expected
    assert query(service, "SELECT count(*) FROM marts.dim_pessoas_cadastro") == [
        (expected["dim_pessoas_cadastro"],)
    ]
    assert query(service, "SELECT count(*) FROM marts.app_cargo_ocupantes") == [
        (expected["app_cargo_ocupantes"],)
    ]


@needs_postgres
def test_the_reader_role_can_select_and_nothing_stays_in_the_staging_schema(
    full: tuple[Connection, Settings], service: duckdb.DuckDBPyConnection
) -> None:
    run(full)
    assert query(service, "SELECT has_table_privilege('leitor', 'marts.dim_pessoas_cadastro', 'SELECT')") == [
        (True,)
    ]
    assert query(service, "SELECT has_table_privilege('leitor', 'marts.dim_pessoas_cadastro', 'INSERT')") == [
        (False,)
    ]
    assert query(service, "SELECT has_table_privilege('leitor', 'marts.app_cargo_ocupantes', 'SELECT')") == [
        (True,)
    ]
    assert query(service, "SELECT has_table_privilege('leitor', 'marts.app_cargo_ocupantes', 'INSERT')") == [
        (False,)
    ]
    assert query(
        service,
        "SELECT count(*) FROM information_schema.schemata WHERE schema_name = 'marts_novo'",
    ) == [(0,)]


@needs_postgres
def test_every_published_table_and_column_carries_its_description(
    full: tuple[Connection, Settings], service: duckdb.DuckDBPyConnection
) -> None:
    run(full)
    tables_without = query(
        service,
        "SELECT c.relname FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
        "WHERE n.nspname = 'marts' AND c.relkind = 'r' AND obj_description(c.oid) IS NULL",
    )
    columns_without = query(
        service,
        "SELECT c.relname || '.' || a.attname FROM pg_attribute a JOIN pg_class c ON c.oid = a.attrelid "
        "JOIN pg_namespace n ON n.oid = c.relnamespace WHERE n.nspname = 'marts' AND c.relkind = 'r' "
        "AND a.attnum > 0 AND NOT a.attisdropped AND col_description(a.attrelid, a.attnum) IS NULL",
    )
    assert (tables_without, columns_without) == ([], [])
    assert query(service, "SELECT obj_description('marts.dim_pessoas_cadastro'::regclass)")[0][0]


@needs_postgres
def test_publishing_again_replaces_the_marts_without_duplicating_rows(
    full: tuple[Connection, Settings], service: duckdb.DuckDBPyConnection
) -> None:
    first = run(full)
    second = publish.publish(replace(full[1], service_dsn=DSN))
    assert first == second
    assert query(service, "SELECT count(*) FROM marts.dim_pessoas_cadastro") == [
        (first["dim_pessoas_cadastro"],)
    ]


def test_publish_without_a_connection_string_explains_what_is_missing(settings: Settings) -> None:
    with pytest.raises(ValueError, match="DADO_PUBLICO_POSTGRES_DSN"):
        publish.publish(settings)


@pytest.mark.parametrize(
    "dsn",
    [
        "postgresql://u:p@localhost:5432/dados",
        "postgresql://u:p@127.0.0.1/dados",
        "host=localhost dbname=dados user=u password=p",
        "host=postgres dbname=dados user=u password=p",
        "dbname=dados user=u",  # sem host: o libpq usa o socket local
        "postgresql://u:p@db.exemplo.org/dados?sslmode=require",
        "postgresql://u:p@db.exemplo.org/dados?sslmode=verify-full",
        "host=db.exemplo.org dbname=dados user=u password=p sslmode=verify-ca",
        "host='db.exemplo.org' sslmode='require'",
    ],
)
def test_a_local_database_or_one_that_requires_tls_is_accepted(dsn: str) -> None:
    publish.require_tls(dsn)


@pytest.mark.parametrize(
    "dsn",
    [
        "postgresql://u:p@db.exemplo.org/dados",
        "postgresql://u:p@db.exemplo.org/dados?sslmode=disable",
        "postgresql://u:p@db.exemplo.org/dados?sslmode=prefer",
        "host=db.exemplo.org dbname=dados user=u password=p",
        "host=db.exemplo.org sslmode=allow",
    ],
)
def test_a_remote_database_without_tls_is_refused(dsn: str) -> None:
    with pytest.raises(ValueError, match="não exige TLS"):
        publish.require_tls(dsn)


def test_publish_refuses_a_remote_dsn_without_tls_before_connecting() -> None:
    settings = Settings(storage_root=Path("."), service_dsn="postgresql://u:p@db.exemplo.org/dados")
    with pytest.raises(ValueError, match="não exige TLS"):
        publish.publish(settings)
