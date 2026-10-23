"""Cópia imutável da identidade de pessoas (ADR 0014).

A chave `id_pessoa` nasce no warehouse e não pode mudar depois de entregue a uma aplicação; reconstruir a
partir do landing não garante as mesmas chaves. Por isso cada execução da identidade grava uma pasta nova
com um Parquet por tabela de `identity`, que nunca é sobrescrita. `problems` confere se a cópia mais
recente ainda é igual ao warehouse.
"""

from datetime import UTC, datetime
from pathlib import Path

from plataforma_dados.core import warehouse
from plataforma_dados.core.settings import Settings
from plataforma_dados.core.warehouse import Connection

SCHEMA = "identity"


def _folder(settings: Settings) -> Path:
    return settings.storage_root / "snapshots" / SCHEMA


def take(con: Connection, settings: Settings) -> Path:
    """Grava a cópia de agora; falha se a pasta já existir (nunca sobrescreve)."""
    target = _folder(settings) / datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    target.mkdir(parents=True)
    for table in warehouse.tables(con, SCHEMA):
        con.execute(f"COPY {SCHEMA}.{table} TO '{(target / f'{table}.parquet').as_posix()}' (FORMAT parquet)")
    return target


def problems(con: Connection, settings: Settings) -> list[str]:
    """A cópia mais recente existe e tem exatamente as linhas do warehouse? Devolve o que diverge."""
    folders = sorted(_folder(settings).glob("*")) if _folder(settings).exists() else []
    if not folders:
        return ["identidade sem snapshot: rode `plataforma identity`"]
    found = []
    for table in warehouse.tables(con, SCHEMA):
        file = (folders[-1] / f"{table}.parquet").as_posix()
        if not Path(file).exists():
            found.append(f"snapshot {folders[-1].name}: falta {table}")
            continue
        live, saved = f"SELECT * FROM {SCHEMA}.{table}", f"SELECT * FROM read_parquet('{file}')"
        diff = warehouse.scalar(
            con,
            f"SELECT (SELECT count(*) FROM ({live} EXCEPT {saved}))"
            f" + (SELECT count(*) FROM ({saved} EXCEPT {live}))",
        )
        if diff:
            found.append(f"snapshot {folders[-1].name}: {table} difere do warehouse em {diff} linhas")
    return found
