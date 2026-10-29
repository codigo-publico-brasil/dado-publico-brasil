"""Começo da reconstrução do warehouse do zero (docs/02-fazer/04-operar-e-publicar.md).

O warehouse se refaz do landing (raw, staging, intermediate, core, fatos, analise, servico e marts) e a
`identity` é criada de novo, com chaves novas. O que NÃO se refaz do landing hoje é o registro das capturas
(URL, data, hash, ETag e itens de cada lote), que mora em `metadata` (issue 153). Por isso a reconstrução
parte do warehouse antigo e leva dele só o `metadata`, marcando as capturas como ainda não carregadas.
"""

from datetime import UTC, datetime
from pathlib import Path

from dado_publico_brasil.core import migrations
from dado_publico_brasil.core.settings import Settings
from dado_publico_brasil.core.warehouse import scalar

TABLES = ("captures", "capture_items", "source_checks", "runs", "dbt_results")
SEQUENCES = (  # (sequência, tabela, coluna): depois de copiar linhas com id, a sequência passa do maior id
    ("seq_captures", "captures", "id"),
    ("seq_capture_items", "capture_items", "id"),
    ("seq_source_checks", "source_checks", "id"),
    ("seq_runs", "runs", "id"),
)


def start_from(settings: Settings, old_warehouse: Path) -> dict[str, int]:
    """Cria o warehouse novo com o `metadata` do antigo e põe de lado o estado do dlt; devolve as linhas.

    Recusa se o warehouse novo já existe (não sobrescreve nada) ou se o antigo não existe.
    """
    if settings.warehouse.exists():
        raise FileExistsError(f"{settings.warehouse} já existe: mova o warehouse antigo antes de reconstruir")
    if not old_warehouse.exists():
        raise FileNotFoundError(f"warehouse antigo não encontrado: {old_warehouse}")
    con = migrations.open_warehouse(settings)
    try:
        con.execute(f"ATTACH '{old_warehouse.as_posix()}' AS old (READ_ONLY)")
        copied = {}
        for table in TABLES:
            con.execute(f"INSERT INTO metadata.{table} BY NAME SELECT * FROM old.metadata.{table}")
            copied[table] = int(scalar(con, f"SELECT count(*) FROM metadata.{table}"))
        con.execute("DETACH old")
        con.execute("UPDATE metadata.captures SET loaded_at = NULL")  # tudo volta a carregar do landing
        for sequence, table, column in SEQUENCES:
            biggest = int(scalar(con, f"SELECT coalesce(max({column}), 0) FROM metadata.{table}"))
            if biggest:
                con.execute(f"SELECT nextval('metadata.{sequence}') FROM range({biggest + 1})").fetchall()
    finally:
        con.close()
    dlt = settings.state_dir / "dlt"
    if dlt.exists():  # o estado antigo diz o que já foi carregado num destino que não existe mais
        dlt.rename(dlt.with_name("dlt.antes-" + datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")))
    return copied
