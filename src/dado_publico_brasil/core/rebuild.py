"""Começo da reconstrução do warehouse do zero (docs/02-fazer/04-operar-e-publicar.md).

O warehouse se refaz do landing (raw, staging, intermediate e marts) e a
`identity` e o registro das capturas (`metadata`: URL, data, hash, ETag e itens de cada lote, issue 153) não
se refazem dele. Eles vêm do bucket privado (ADR 0036, mesmas chaves) ou, com `--old-warehouse`, do warehouse
antigo (só o `metadata`; a identidade nasce de novo). Em ambos as capturas voltam como não carregadas.
O warehouse antigo precisa estar com as migrações em dia (a versão atual as aplica ao abri-lo).
"""

from datetime import UTC, datetime
from pathlib import Path

from dado_publico_brasil.core import migrations
from dado_publico_brasil.core.settings import Settings
from dado_publico_brasil.core.warehouse import Connection, scalar

TABLES = ("capturas", "capturas_itens", "fontes_verificacoes", "execucoes", "testes_resultados")
SEQUENCES = (  # (sequência, tabela, coluna): depois de copiar linhas com id, a sequência passa do maior id
    ("identity.seq_pessoas", "identity.pessoas", "id_pessoa"),
    ("metadata.seq_capturas", "metadata.capturas", "id_captura"),
    ("metadata.seq_capturas_itens", "metadata.capturas_itens", "id_captura_item"),
    ("metadata.seq_fontes_verificacoes", "metadata.fontes_verificacoes", "id_verificacao"),
    ("metadata.seq_execucoes", "metadata.execucoes", "id_execucao"),
)


def advance_sequences(con: Connection) -> None:
    """Põe cada sequência além do maior id já copiado, para nunca repetir uma chave."""
    for sequence, table, column in SEQUENCES:
        biggest = int(scalar(con, f"SELECT coalesce(max({column}), 0) FROM {table}"))
        if biggest:
            con.execute(f"SELECT nextval('{sequence}') FROM range({biggest + 1})").fetchall()


def start_from(settings: Settings, old_warehouse: Path | None = None) -> dict[str, int]:
    """Cria o warehouse novo e põe de lado o estado do dlt; devolve as linhas do `metadata`.

    O `registry.duckdb` não depende do warehouse: se já existe, fica como está e só as capturas voltam a
    carregar. Senão, com `old_warehouse` (anterior ao ADR 0051, com o `metadata` dentro), leva dele o
    `metadata` (a identidade é criada de novo); sem ele, restaura do bucket privado o `metadata` e a
    identidade, com as mesmas chaves (ADR 0036). Recusa se o warehouse novo já existe.
    """
    from dado_publico_brasil.core import privado  # privado importa este módulo

    migrations.adopt_registry(settings)
    if settings.warehouse.exists():
        raise FileExistsError(f"{settings.warehouse} já existe: mova o warehouse antigo antes de reconstruir")
    if old_warehouse is not None and settings.registry.exists():
        raise FileExistsError(
            f"{settings.registry} já existe: ele guarda o registry, omita o warehouse antigo"
        )
    if old_warehouse is None and not settings.registry.exists() and privado.root(settings) is None:
        raise FileNotFoundError(f"sem warehouse antigo e sem {privado.ENV}: nada de onde restaurar")
    if old_warehouse is not None and not old_warehouse.exists():
        raise FileNotFoundError(f"warehouse antigo não encontrado: {old_warehouse}")
    con = migrations.open_warehouse(settings, restore=old_warehouse is None)
    try:
        if old_warehouse is not None:
            con.execute(f"ATTACH '{old_warehouse.as_posix()}' AS old (READ_ONLY)")
            for table in TABLES:
                con.execute(f"INSERT INTO metadata.{table} BY NAME SELECT * FROM old.metadata.{table}")
            con.execute("DETACH old")
            advance_sequences(con)
        con.execute("UPDATE metadata.capturas SET dt_carga = NULL")  # tudo volta a carregar do landing
        copied = {t: int(scalar(con, f"SELECT count(*) FROM metadata.{t}")) for t in TABLES}
    finally:
        con.close()
    dlt = settings.state_dir / "dlt"
    if dlt.exists():  # o estado antigo diz o que já foi carregado num destino que não existe mais
        dlt.rename(dlt.with_name("dlt.antes-" + datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")))
    return copied
