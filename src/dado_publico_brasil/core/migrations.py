"""Aplica as migrações numeradas de `ddl/` (`NNNN_descricao.sql`): tabelas `metadata.*` e `identity.*`.

Só estas tabelas têm migração, porque não se reconstroem do raw: o resto é criado e evoluído por dlt
(raw) e dbt (staging, intermediate, marts). Cada arquivo roda uma vez, em ordem. Instruções separadas
por `;` no fim da linha. Cada arquivo e o seu registro rodam numa transação.
"""

import re
from pathlib import Path

from dado_publico_brasil.core import warehouse
from dado_publico_brasil.core.runs import now
from dado_publico_brasil.core.settings import DDL_DIR, Settings
from dado_publico_brasil.core.warehouse import Connection

PATTERN = re.compile(r"^(\d{4})_[\w-]+\.sql$")


def _ledger(con: Connection) -> str:
    """Nome da tabela que registra as migrações: `migrations` até a 0007, que a renomeia para `migracoes`."""
    renamed = con.execute(
        "SELECT count(*) FROM duckdb_tables() WHERE schema_name = 'metadata' AND table_name = 'migracoes'"
    ).fetchone()
    return "migracoes" if renamed and renamed[0] else "migrations"


def apply(con: Connection, directory: Path = DDL_DIR) -> list[str]:
    """Aplica as migrações pendentes de `directory`. Devolve as versões aplicadas."""
    con.execute("CREATE SCHEMA IF NOT EXISTS metadata")
    if _ledger(con) == "migrations":  # warehouse novo ou anterior à 0007
        con.execute(
            "CREATE TABLE IF NOT EXISTS metadata.migrations "
            "(version VARCHAR PRIMARY KEY, applied_at VARCHAR NOT NULL)"
        )
    done = {row[0] for row in con.execute(f"SELECT * FROM metadata.{_ledger(con)}").fetchall()}
    applied = []
    for file in sorted(directory.glob("*.sql")):
        match = PATTERN.match(file.name)
        if not match or match.group(1) in done:
            continue
        con.execute("BEGIN")  # arquivo e registro numa transação: falha no meio não deixa nada aplicado
        try:
            for statement in re.split(r";\s*\n", file.read_text(encoding="utf-8")):
                if statement.strip():
                    con.execute(statement)
            con.execute(f"INSERT INTO metadata.{_ledger(con)} VALUES (?, ?)", (match.group(1), now()))
        except BaseException:
            con.execute("ROLLBACK")
            raise
        con.execute("COMMIT")
        applied.append(match.group(1))
    return applied


def open_warehouse(settings: Settings, restore: bool = True) -> Connection:
    """Abre o warehouse para escrita e aplica as migrações pendentes.

    Arquivo novo com o bucket privado configurado: restaura dele o metadata e a identidade (ADR 0036).
    """
    from dado_publico_brasil.core import privado  # privado importa rebuild, que importa este módulo

    new = not settings.warehouse.exists()
    con = warehouse.connect(settings)
    apply(con)
    if new and restore:
        privado.restore(con, settings)
    return con
