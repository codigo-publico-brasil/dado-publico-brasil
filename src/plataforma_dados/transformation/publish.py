"""Publica os marts no PostgreSQL de serviço (ADR 0014): as aplicações leem de lá, nunca do DuckDB.

Os marts são copiados para um esquema novo (`marts_novo`) sem tocar no que está no ar e trocados num único
comando atômico: quem lê vê ou os marts antigos ou os novos, nunca metade. O papel `leitor` (somente leitura)
é criado pela infraestrutura, não por este código. Usa a extensão `postgres` do DuckDB; a primeira execução
baixa a extensão.
"""

import duckdb

from plataforma_dados.core.settings import Settings

READER = "leitor"
LIVE = "marts"
STAGING = "marts_novo"


def _quote(text: str) -> str:
    return text.replace("'", "''")


def _count(con: duckdb.DuckDBPyConnection, sql: str) -> int:
    row = con.execute(sql).fetchone()
    return int(row[0]) if row else 0


def publish(settings: Settings) -> dict[str, int]:
    """Copia cada tabela de `marts` e devolve as linhas publicadas por tabela."""
    if not settings.service_dsn:
        raise ValueError("defina PLATAFORMA_POSTGRES_DSN (veja .env.example)")
    con = duckdb.connect()
    try:
        con.execute("INSTALL postgres")
        con.execute("LOAD postgres")
        con.execute(f"ATTACH '{_quote(settings.warehouse.as_posix())}' AS wh (READ_ONLY)")
        con.execute(f"ATTACH '{_quote(settings.service_dsn)}' AS service (TYPE postgres)")
        names = [
            t
            for (t,) in con.execute(
                "SELECT table_name FROM duckdb_tables() "
                "WHERE database_name = 'wh' AND schema_name = ? ORDER BY 1",
                (LIVE,),
            ).fetchall()
        ]
        con.execute(f"DROP SCHEMA IF EXISTS service.{STAGING} CASCADE")
        con.execute(f"CREATE SCHEMA service.{STAGING}")
        for name in names:
            con.execute(f"CREATE TABLE service.{STAGING}.{name} AS SELECT * FROM wh.{LIVE}.{name}")
        swap = (
            f"DROP SCHEMA IF EXISTS {LIVE} CASCADE; ALTER SCHEMA {STAGING} RENAME TO {LIVE}; "
            f"GRANT USAGE ON SCHEMA {LIVE} TO {READER}; "
            f"GRANT SELECT ON ALL TABLES IN SCHEMA {LIVE} TO {READER}"
        )
        con.execute(f"CALL postgres_execute('service', '{swap}')")
        published = {
            name: _count(
                con, f"SELECT * FROM postgres_query('service', 'SELECT count(*) FROM {LIVE}.{name}')"
            )
            for name in names
        }
        sent = {name: _count(con, f"SELECT count(*) FROM wh.{LIVE}.{name}") for name in names}
        if published != sent:
            raise RuntimeError(f"publicação divergente: {published} <> {sent}")
        return published
    finally:
        con.close()
