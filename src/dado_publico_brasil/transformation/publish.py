"""Publica o esquema `marts` no PostgreSQL de serviço (ADR 0014 e 0033): as aplicações leem de lá.

Nunca leem do DuckDB. O esquema é copiado para um esquema novo (`marts_novo`) sem tocar no que está no ar e
trocado num único comando atômico: quem lê vê ou os dados antigos ou os novos, nunca metade. O papel `leitor`
(somente leitura) é criado pela infraestrutura, não por este código. As views `app_` viram tabelas.
Usa a extensão `postgres` do DuckDB; a primeira execução baixa a extensão.
"""

import re
from urllib.parse import parse_qs, urlparse

import duckdb

from dado_publico_brasil.core.settings import Settings

READER = "leitor"
LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1", "postgres"}  # "postgres": o serviço do compose.yaml
SECURE_MODES = {"require", "verify-ca", "verify-full"}
SCHEMAS = ("marts",)  # o que vai para o Postgres; o resto do warehouse fica no DuckDB


def require_tls(dsn: str) -> None:
    """Recusa o DSN de um servidor não local que não exija TLS (`sslmode` require, verify-ca ou verify-full).

    Em produção a senha e os dados do serviço não podem trafegar sem criptografia (issue 37). Aceita os
    dois formatos do libpq: a URL (`postgresql://...?sslmode=require`) e `chave=valor`.
    """
    if "://" in dsn:
        url = urlparse(dsn)
        host = url.hostname or ""
        mode = (parse_qs(url.query).get("sslmode") or [""])[0]
    else:
        pairs = dict(re.findall(r"(\w+)\s*=\s*'?([^'\s]+)'?", dsn))
        host = pairs.get("host", "localhost")
        mode = pairs.get("sslmode", "")
    if host in LOCAL_HOSTS or mode in SECURE_MODES:
        return
    raise ValueError(
        f"o DSN do servidor '{host}' não exige TLS: acrescente sslmode=require (ou verify-full) em "
        "DADO_PUBLICO_POSTGRES_DSN; só o banco local dispensa"
    )


def _quote(text: str) -> str:
    return text.replace("'", "''")


def _count(con: duckdb.DuckDBPyConnection, sql: str) -> int:
    row = con.execute(sql).fetchone()
    return int(row[0]) if row else 0


def _relations(con: duckdb.DuckDBPyConnection, catalog: str, schema: str) -> list[str]:
    """As tabelas e views de um esquema do warehouse."""
    return [
        name
        for (name,) in con.execute(
            f"SELECT table_name FROM duckdb_tables() WHERE database_name = '{catalog}' AND schema_name = ? "
            f"UNION SELECT view_name FROM duckdb_views() WHERE database_name = '{catalog}' "
            "AND schema_name = ? AND NOT internal ORDER BY 1",
            (schema, schema),
        ).fetchall()
    ]


def _comments(con: duckdb.DuckDBPyConnection, catalog: str, schema: str) -> str:
    """`COMMENT ON` de cada tabela, view e coluna de um esquema, lidos do DuckDB, para o Postgres."""

    def text(value: str) -> str:
        return "'" + value.replace("'", "''") + "'"

    staging = f"{schema}_novo"
    statements = [
        f'COMMENT ON TABLE {staging}."{table}" IS {text(comment)}'
        for table, comment in con.execute(
            "SELECT table_name, comment FROM duckdb_tables() "
            f"WHERE database_name = '{catalog}' AND schema_name = ? AND comment IS NOT NULL "
            "UNION SELECT view_name, comment FROM duckdb_views() "
            f"WHERE database_name = '{catalog}' AND schema_name = ? AND comment IS NOT NULL AND NOT internal",
            (schema, schema),
        ).fetchall()
    ]
    statements += [
        f'COMMENT ON COLUMN {staging}."{table}"."{column}" IS {text(comment)}'
        for table, column, comment in con.execute(
            "SELECT table_name, column_name, comment FROM duckdb_columns() "
            f"WHERE database_name = '{catalog}' AND schema_name = ? AND comment IS NOT NULL",
            (schema,),
        ).fetchall()
    ]
    return "; ".join(statements)


def _publish_schema(con: duckdb.DuckDBPyConnection, catalog: str, schema: str) -> dict[str, int]:
    """Copia as tabelas e views de um esquema e troca o esquema no ar. Devolve as linhas por nome."""
    staging = f"{schema}_novo"
    names = _relations(con, catalog, schema)
    con.execute(f"DROP SCHEMA IF EXISTS service.{staging} CASCADE")
    con.execute(f"CREATE SCHEMA service.{staging}")
    for name in names:
        con.execute(f"CREATE TABLE service.{staging}.{name} AS SELECT * FROM {catalog}.{schema}.{name}")
    comments = _comments(con, catalog, schema)
    if comments:
        con.execute(f"CALL postgres_execute('service', '{_quote(comments)}')")  # descrições, como no DuckDB
    swap = (
        f"DROP SCHEMA IF EXISTS {schema} CASCADE; ALTER SCHEMA {staging} RENAME TO {schema}; "
        f"GRANT USAGE ON SCHEMA {schema} TO {READER}; "
        f"GRANT SELECT ON ALL TABLES IN SCHEMA {schema} TO {READER}"
    )
    con.execute(f"CALL postgres_execute('service', '{swap}')")
    published = {
        name: _count(con, f"SELECT * FROM postgres_query('service', 'SELECT count(*) FROM {schema}.{name}')")
        for name in names
    }
    sent = {name: _count(con, f"SELECT count(*) FROM {catalog}.{schema}.{name}") for name in names}
    if published != sent:
        raise RuntimeError(f"publicação divergente em {schema}: {published} <> {sent}")
    return published


def publish(settings: Settings) -> dict[str, int]:
    """Publica os marts; devolve as linhas por tabela."""
    if not settings.service_dsn:
        raise ValueError("defina DADO_PUBLICO_POSTGRES_DSN (veja .env.example)")
    require_tls(settings.service_dsn)
    catalog = settings.warehouse.stem  # as views do dbt citam o banco pelo nome do arquivo
    con = duckdb.connect()
    try:
        con.execute("INSTALL postgres")
        con.execute("LOAD postgres")
        con.execute(f"ATTACH '{_quote(settings.warehouse.as_posix())}' AS {catalog} (READ_ONLY)")
        con.execute(f"ATTACH '{_quote(settings.service_dsn)}' AS service (TYPE postgres)")
        published: dict[str, int] = {}
        for schema in SCHEMAS:
            published |= _publish_schema(con, catalog, schema)
        return published
    finally:
        con.close()
