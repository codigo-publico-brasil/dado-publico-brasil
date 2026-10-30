"""Acesso ao data warehouse (DuckDB, um arquivo; esquemas por camada).

Um arquivo DuckDB aceita um processo escritor por vez (ou vários leitores). Por isso o dbt roda em
outro processo, com a conexão do chamador fechada, e a aplicação abre em modo somente leitura.
"""

from typing import Any

import duckdb

from dado_publico_brasil.core.settings import Settings

Connection = duckdb.DuckDBPyConnection

# O padrão do DuckDB é 80% da RAM; num container isso deixa pouco para o sistema, e ler ou escrever o
# arquivo falha com "Cannot allocate memory" (issue 160). O que passa do teto vai para o disco. Vale para
# conexões que não dividem o arquivo com outra do mesmo processo (o publish e o perfil do dbt): o DuckDB
# recusa abrir o mesmo arquivo com configuração diferente, e o dlt abre o warehouse por conta própria,
# então `connect` não a aplica.
CONFIG: dict[str, str | bool | int | float | list[str]] = {"memory_limit": "5GB"}


def connect(settings: Settings, read_only: bool = False) -> Connection:
    path = settings.warehouse
    if read_only:
        return duckdb.connect(str(path), read_only=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(str(path))


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
