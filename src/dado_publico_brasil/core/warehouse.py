"""Acesso ao data warehouse (DuckDB, esquemas por camada) e ao `estado.duckdb` (ADR 0051).

Um arquivo DuckDB aceita um processo escritor por vez (ou vários leitores). Por isso o dbt roda em
outro processo, com a conexão do chamador fechada, e a aplicação abre em modo somente leitura.

O `metadata` e a `identity` moram em `estado.duckdb`, anexado como `estado`. O `search_path` os põe ao
alcance do nome curto (`metadata.capturas`), e o `main` na frente mantém o warehouse como catálogo padrão.
"""

import os
from typing import Any

import duckdb

from dado_publico_brasil.core.settings import Settings

Connection = duckdb.DuckDBPyConnection
SEARCH_PATH = "main,estado.metadata,estado.identity"


def connect(settings: Settings, read_only: bool = False) -> Connection:
    path = settings.warehouse
    if not read_only:
        path.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(path), read_only=read_only)
    estado = settings.estado
    if not read_only or estado.exists():
        con.execute(f"ATTACH '{estado.as_posix()}' AS estado" + (" (READ_ONLY)" if read_only else ""))
        if not read_only:
            con.execute("CREATE SCHEMA IF NOT EXISTS estado.metadata")
            con.execute("CREATE SCHEMA IF NOT EXISTS estado.identity")
        con.execute(f"SET search_path = '{SEARCH_PATH}'")
    # `SET`, não `config=`: outra conexão ao mesmo arquivo (o dlt) com configuração diferente é recusada
    con.execute(f"SET memory_limit = '{os.environ.get('DADO_PUBLICO_DUCKDB_MEMORY', '80%')}'")
    return con


def cursor(con: Connection) -> Connection:
    """Cursor de leitura que herda o `search_path` da conexão (o `cursor()` do DuckDB não o herda)."""
    cur = con.cursor()
    if cur.execute("SELECT count(*) FROM duckdb_databases() WHERE database_name = 'estado'").fetchone() != (
        0,
    ):
        cur.execute(f"SET search_path = '{SEARCH_PATH}'")
    return cur


def replace_view(con: Connection, schema: str, name: str, select: str) -> None:
    """`CREATE OR REPLACE VIEW` que mantém as descrições (o DuckDB as perde ao refazer a view)."""
    comments = rows(
        con,
        "SELECT NULL AS column_name, comment FROM duckdb_views() WHERE schema_name = ? AND view_name = ? "
        "AND comment IS NOT NULL UNION ALL SELECT column_name, comment FROM duckdb_columns() "
        "WHERE schema_name = ? AND table_name = ? AND comment IS NOT NULL",
        (schema, name, schema, name),
    )
    con.execute(f'CREATE OR REPLACE VIEW "{schema}"."{name}" AS {select}')
    kept = set(columns(con, schema, name))
    for c in comments:
        text = "'" + c["comment"].replace("'", "''") + "'"
        if c["column_name"] is None:
            con.execute(f'COMMENT ON VIEW "{schema}"."{name}" IS {text}')
        elif c["column_name"] in kept:
            con.execute(f'COMMENT ON COLUMN "{schema}"."{name}"."{c["column_name"]}" IS {text}')


def scalar(con: Connection, sql: str, params: tuple[Any, ...] = ()) -> Any:
    row = con.execute(sql, params).fetchone()
    return row[0] if row else None


def rows(con: Connection, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    result = con.execute(sql, params)
    names = [d[0] for d in result.description]
    return [dict(zip(names, row, strict=True)) for row in result.fetchall()]


def tables(con: Connection, schema: str) -> list[str]:
    found = con.execute(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema = ? AND table_name NOT LIKE '\\_dlt\\_%' ESCAPE '\\' ORDER BY 1",
        (schema,),
    ).fetchall()
    return [t for (t,) in found]


def columns(con: Connection, schema: str, table: str) -> list[str]:
    found = con.execute(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_schema = ? AND table_name = ? ORDER BY ordinal_position",
        (schema, table),
    ).fetchall()
    return [c for (c,) in found]
