"""Aplica as migrações numeradas de `ddl/` (`NNNN_descricao.sql`): tabelas `metadata.*` e `identity.*`.

Só estas tabelas têm migração, porque não se reconstroem do raw: o resto é criado e evoluído por dlt
(raw) e dbt (staging, intermediate, marts). Cada arquivo roda uma vez, em ordem. Instruções separadas
por `;` no fim da linha.
"""

import re
from pathlib import Path

from plataforma_dados.core import warehouse
from plataforma_dados.core.runs import now
from plataforma_dados.core.settings import DDL_DIR, Settings
from plataforma_dados.core.warehouse import Connection

PATTERN = re.compile(r"^(\d{4})_[\w-]+\.sql$")


def apply(con: Connection, directory: Path = DDL_DIR) -> list[str]:
    """Aplica as migrações pendentes de `directory`. Devolve as versões aplicadas."""
    con.execute("CREATE SCHEMA IF NOT EXISTS metadata")
    con.execute(
        "CREATE TABLE IF NOT EXISTS metadata.migrations "
        "(version VARCHAR PRIMARY KEY, applied_at VARCHAR NOT NULL)"
    )
    done = {v for (v,) in con.execute("SELECT version FROM metadata.migrations").fetchall()}
    applied = []
    for file in sorted(directory.glob("*.sql")):
        match = PATTERN.match(file.name)
        if not match or match.group(1) in done:
            continue
        for statement in re.split(r";\s*\n", file.read_text(encoding="utf-8")):
            if statement.strip():
                con.execute(statement)
        con.execute("INSERT INTO metadata.migrations VALUES (?, ?)", (match.group(1), now()))
        applied.append(match.group(1))
    return applied


def open_warehouse(settings: Settings) -> Connection:
    """Abre o warehouse para escrita e aplica as migrações pendentes."""
    con = warehouse.connect(settings)
    apply(con)
    return con
