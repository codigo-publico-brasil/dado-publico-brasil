"""Warehouse anterior ao ADR 0051: `metadata` e `identity` dentro do mesmo arquivo (para testar a migração)."""

import re

import duckdb

from dado_publico_brasil.core.settings import DDL_DIR, Settings


def make(settings: Settings) -> None:
    """Cria o arquivo do warehouse com as migrações de `ddl/` aplicadas nele, como a versão anterior fazia."""
    settings.warehouse.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(settings.warehouse))
    try:
        con.execute("CREATE SCHEMA metadata")
        con.execute(
            "CREATE TABLE metadata.migrations (version VARCHAR PRIMARY KEY, applied_at VARCHAR NOT NULL)"
        )
        for file in sorted(DDL_DIR.glob("*.sql")):
            for statement in re.split(r";\s*\n", file.read_text(encoding="utf-8")):
                if statement.strip():
                    con.execute(statement)
        con.execute("CREATE SCHEMA raw_x")
        con.execute("CREATE TABLE raw_x.t AS SELECT 1 AS a")
        con.execute(
            "INSERT INTO metadata.capturas (id_captura, fonte, dataset, particao, url, sha256, qtd_bytes, caminho, "
            "dt_captura, dt_verificacao, dt_carga) VALUES (40, 'fonte_a', 'conjunto', 2024, 'https://x/a', 'abc', 1, "
            "'p', '2026-10-20', '2026-10-21', '2026-10-22')"
        )
        con.execute(
            "INSERT INTO metadata.fontes_verificacoes (id_verificacao, dt_verificacao, fonte, dataset, verificacao, "
            "resultado, detalhe) VALUES (90, '2026-10-21', 'fonte_a', 'conjunto', 'carga', 'ok', 'x')"
        )
        con.execute("INSERT INTO identity.pessoas VALUES (7, '2026-10-23 00:00:00')")
    finally:
        con.close()
