"""Cópia imutável da identidade de pessoas (ADR 0014).

A chave `id_pessoa` nasce no warehouse e não pode mudar depois de entregue a uma aplicação; reconstruir a
partir do landing não garante as mesmas chaves. Por isso, quando a identidade MUDA, grava-se uma pasta nova
com um Parquet por tabela de `identity` (compactado), que nunca é sobrescrita. Se a identidade é igual à cópia
mais recente, nada é gravado: a cópia nova seria idêntica e só ocuparia espaço (a pipeline roda várias
vezes por dia e a identidade quase nunca muda). `problems` confere se a cópia mais recente ainda é igual
ao warehouse.
"""

from datetime import UTC, datetime
from pathlib import Path

from dado_publico_brasil.core import warehouse
from dado_publico_brasil.core.settings import Settings
from dado_publico_brasil.core.warehouse import Connection

SCHEMA = "identity"


def _folder(settings: Settings) -> Path:
    return settings.storage_root / "snapshots" / SCHEMA


def _latest(settings: Settings) -> Path | None:
    folders = sorted(_folder(settings).glob("*")) if _folder(settings).exists() else []
    return folders[-1] if folders else None


def _differences(con: Connection, folder: Path) -> list[str]:
    """O que a cópia `folder` tem de diferente do warehouse, por tabela (vazio: são iguais)."""
    found = []
    for table in warehouse.tables(con, SCHEMA):
        file = (folder / f"{table}.parquet").as_posix()
        if not Path(file).exists():
            found.append(f"snapshot {folder.name}: falta {table}")
            continue
        live, saved = f"SELECT * FROM {SCHEMA}.{table}", f"SELECT * FROM read_parquet('{file}')"
        diff = warehouse.scalar(
            con,
            f"SELECT (SELECT count(*) FROM ({live} EXCEPT {saved}))"
            f" + (SELECT count(*) FROM ({saved} EXCEPT {live}))",
        )
        if diff:
            found.append(f"snapshot {folder.name}: {table} difere do warehouse em {diff} linhas")
    return found


def take(con: Connection, settings: Settings) -> Path | None:
    """Grava a cópia de agora, se a identidade mudou desde a mais recente; devolve a pasta nova ou None.

    Nunca sobrescreve: falha se a pasta já existir.
    """
    latest = _latest(settings)
    if latest is not None and not _differences(con, latest):
        return None
    target = _folder(settings) / datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    target.mkdir(parents=True)
    for table in warehouse.tables(con, SCHEMA):
        con.execute(
            f"COPY {SCHEMA}.{table} TO '{(target / f'{table}.parquet').as_posix()}' "
            "(FORMAT parquet, COMPRESSION zstd)"
        )
    return target


def problems(con: Connection, settings: Settings) -> list[str]:
    """A cópia mais recente existe e tem exatamente as linhas do warehouse? Devolve o que diverge."""
    latest = _latest(settings)
    if latest is None:
        return ["identidade sem snapshot: rode `dado-publico identity`"]
    return _differences(con, latest)
