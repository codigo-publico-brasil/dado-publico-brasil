"""Aplica as migrações numeradas de `ddl/` (`NNNN_descricao.sql`): tabelas `metadata.*` e `identity.*`.

Só estas tabelas têm migração, porque não se reconstroem do raw: o resto é criado e evoluído por dlt
(raw) e dbt (staging, intermediate, marts). Cada arquivo roda uma vez, em ordem. Instruções separadas
por `;` no fim da linha. Cada arquivo e o seu registro rodam numa transação.
"""

import logging
import re
from pathlib import Path

import duckdb

from dado_publico_brasil.core import warehouse
from dado_publico_brasil.core.runs import now
from dado_publico_brasil.core.settings import DDL_DIR, REGISTRY_LEGADO_FILE, Settings
from dado_publico_brasil.core.warehouse import Connection

logger = logging.getLogger(__name__)

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


LEDGERS = ("migrations", "migracoes")


def _legacy_schemas(settings: Settings) -> list[str]:
    """Esquemas `metadata` e `identity` que ainda moram no warehouse (anterior ao ADR 0051)."""
    if not settings.warehouse.exists():
        return []
    con = duckdb.connect(str(settings.warehouse), read_only=True)
    try:
        found = con.execute(
            "SELECT DISTINCT schema_name FROM duckdb_tables() WHERE schema_name IN ('metadata', 'identity')"
        ).fetchall()
    finally:
        con.close()
    return sorted(s for (s,) in found)


def _fingerprint(con: Connection, source: str, table: str, columns: list[str]) -> tuple[int, int]:
    """Contagem e soma do hash das linhas, nas colunas dadas: prova que a cópia é igual à origem."""
    cols = ", ".join(f'"{c}"' for c in columns)
    row = con.execute(
        f"SELECT count(*), coalesce(sum(hash({cols})::HUGEINT), 0)::HUGEINT FROM {source}{table}"
    ).fetchone()
    assert row is not None
    return int(row[0]), int(row[1])


def migrate_legacy(settings: Settings, schemas: list[str]) -> dict[str, int]:
    """Copia `metadata` e `identity` do warehouse para o `registry.duckdb` e só então os apaga do warehouse.

    A cópia e a prova (contagem e soma de hash por tabela) rodam numa transação do registry; se divergirem,
    nada é apagado do warehouse. Repetível: uma queda depois da cópia e antes do `DROP` refaz a cópia.
    """
    from dado_publico_brasil.core import rebuild  # rebuild importa este módulo

    settings.registry.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(settings.registry))  # o catálogo padrão é o registry: o DDL vale sem qualificar
    copied: dict[str, int] = {}
    try:
        apply(con)
        con.execute(f"ATTACH '{settings.warehouse.as_posix()}' AS legado (READ_ONLY)")
        found = con.execute(
            "SELECT schema_name, table_name FROM duckdb_tables() WHERE database_name = 'legado' "
            "AND schema_name IN (SELECT unnest(?)) AND table_name NOT IN (SELECT unnest(?)) ORDER BY 1, 2",
            (schemas, list(LEDGERS)),
        ).fetchall()
        con.execute("BEGIN")
        try:
            for schema, table in found:
                cols = [
                    c
                    for (c,) in con.execute(
                        "SELECT column_name FROM duckdb_columns() WHERE database_name = current_database() "
                        "AND schema_name = ? AND table_name = ?",
                        (schema, table),
                    ).fetchall()
                ]
                old_cols = con.execute(
                    "SELECT column_name FROM duckdb_columns() WHERE database_name = 'legado' "
                    "AND schema_name = ? AND table_name = ? ORDER BY column_index",
                    (schema, table),
                ).fetchall()
                common = [c for (c,) in old_cols if c in cols]
                if len(common) != len(old_cols):
                    raise RuntimeError(
                        f"legado.{schema}.{table} tem coluna que o registry não tem: migre antes"
                    )
                list_ = ", ".join(f'"{c}"' for c in common)
                con.execute(f"DELETE FROM {schema}.{table}")
                con.execute(
                    f"INSERT INTO {schema}.{table} ({list_}) SELECT {list_} FROM legado.{schema}.{table}"
                )
                here = _fingerprint(con, f"{schema}.", table, common)
                there = _fingerprint(con, f"legado.{schema}.", table, common)
                if here != there:
                    raise RuntimeError(f"{schema}.{table}: cópia diferente da origem ({here} contra {there})")
                copied[f"{schema}.{table}"] = here[0]
        except BaseException:
            con.execute("ROLLBACK")
            raise
        con.execute("COMMIT")
        con.execute("DETACH legado")
        rebuild.advance_sequences(con)
    finally:
        con.close()
    legacy = duckdb.connect(str(settings.warehouse))
    try:
        legacy.execute("BEGIN")
        for schema in schemas:
            legacy.execute(f"DROP SCHEMA {schema} CASCADE")
        legacy.execute("COMMIT")
    finally:
        legacy.close()
    return copied


def adopt_registry(settings: Settings) -> None:
    """Renomeia o `estado.duckdb` (nome anterior ao ADR 0060) para `registry.duckdb`, sem copiar nem apagar.

    O `.wal` vai primeiro: uma queda no meio deixa `estado.duckdb` inteiro e a próxima abertura refaz.
    Com os dois arquivos, vale o `registry.duckdb` e o antigo não é tocado.
    """
    old = settings.registry.with_name(REGISTRY_LEGADO_FILE)
    if not old.exists():
        return
    if settings.registry.exists():
        logger.warning(
            "%s e %s existem: usando %s; %s não foi tocado",
            old,
            settings.registry,
            settings.registry.name,
            old.name,
        )
        return
    for src, dst in (
        (old.with_name(old.name + ".wal"), settings.registry.with_name(settings.registry.name + ".wal")),
        (old, settings.registry),
    ):
        if src.exists():
            src.rename(dst)
    logger.info("%s renomeado para %s (ADR 0060)", old.name, settings.registry.name)


def open_warehouse(settings: Settings, restore: bool = True) -> Connection:
    """Abre o warehouse (com o registry anexado) para escrita e aplica as migrações pendentes.

    Warehouse anterior ao ADR 0051 (com `metadata` e `identity` dentro): leva-os ao `registry.duckdb`.
    Registry novo com o bucket privado configurado: restaura dele o metadata e a identidade (ADR 0036).
    Se a migração ou a restauração falhar num arquivo recém-criado, ele é apagado: um arquivo pela metade
    faria a próxima subida pular a restauração.
    """
    from dado_publico_brasil.core import privado  # privado importa rebuild, que importa este módulo

    adopt_registry(settings)
    new = not settings.registry.exists()
    new_warehouse = not settings.warehouse.exists()
    con: Connection | None = None
    migrated = False  # depois de migrar, o registry é a única cópia: nunca se apaga
    try:
        legacy = _legacy_schemas(settings)
        if legacy:
            migrate_legacy(settings, legacy)
            migrated = True
        con = warehouse.connect(settings)
        apply(con)
        if new and restore and not legacy:
            privado.restore(con, settings)
    except BaseException:
        if con is not None:
            con.close()
        for file, created in (
            (settings.registry, new and not migrated),
            (settings.warehouse, new_warehouse and not migrated),
        ):
            for f in (file, file.with_name(file.name + ".wal")) if created else ():
                f.unlink(missing_ok=True)
        raise
    return con
