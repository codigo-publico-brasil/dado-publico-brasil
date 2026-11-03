"""Cópia imutável da identidade de pessoas (ADR 0014).

A chave `id_pessoa` nasce no warehouse e não pode mudar depois de entregue a uma aplicação; reconstruir a
partir do landing não garante as mesmas chaves. Por isso, quando a identidade MUDA, grava-se uma pasta nova
com um Parquet por tabela de `identity` (compactado), que nunca é sobrescrita. Com o bucket privado
configurado (ADR 0036) a pasta vai para o R2, fonte da verdade da identidade. Se a identidade é igual à cópia
mais recente, nada é gravado: a cópia nova seria idêntica e só ocuparia espaço (a pipeline roda várias
vezes por dia e a identidade quase nunca muda). `problems` confere se a cópia mais recente ainda é igual
ao warehouse.
"""

from datetime import UTC, datetime

from dado_publico_brasil.core import privado, warehouse
from dado_publico_brasil.core.settings import Settings
from dado_publico_brasil.core.warehouse import Connection

SCHEMA = "identity"


def _differences(con: Connection, folder: str) -> list[str]:
    """O que a cópia `folder` tem de diferente do warehouse, por tabela (vazio: são iguais)."""
    found = []
    name = folder.rsplit("/", 1)[1]
    have = set(privado.files(con, f"{folder}/*.parquet"))
    for table in warehouse.tables(con, SCHEMA):
        file = f"{folder}/{table}.parquet"
        if file not in have:
            found.append(f"snapshot {name}: falta {table}")
            continue
        live, saved = f"SELECT * FROM {SCHEMA}.{table}", f"SELECT * FROM read_parquet('{file}')"
        diff = warehouse.scalar(
            con,
            f"SELECT (SELECT count(*) FROM ({live} EXCEPT {saved}))"
            f" + (SELECT count(*) FROM ({saved} EXCEPT {live}))",
        )
        if diff:
            found.append(f"snapshot {name}: {table} difere do warehouse em {diff} linhas")
    return found


def take(con: Connection, settings: Settings) -> str | None:
    """Grava a cópia de agora, se a identidade mudou desde a mais recente; devolve a pasta nova ou None.

    Com o bucket privado, a pasta vai para lá e o marcador `_concluido` é gravado por último: pasta sem
    marcador é ignorada. Nunca sobrescreve. Falha (e a execução para) se o envio falhar.
    """
    privado.secret(con)
    latest = privado.latest(con, settings)
    if latest is not None and not _differences(con, latest):
        return None
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    target = privado.prepare(f"{privado.snapshots(settings)}/{stamp}")
    for table in warehouse.tables(con, SCHEMA):
        con.execute(f"COPY {SCHEMA}.{table} TO '{target}/{table}.parquet' (FORMAT parquet, COMPRESSION zstd)")
    con.execute(f"COPY (SELECT now() AS dt_conclusao) TO '{target}/{privado.MARKER}' (FORMAT csv)")
    return target


def problems(con: Connection, settings: Settings) -> list[str]:
    """A cópia mais recente existe e tem exatamente as linhas do warehouse? Devolve o que diverge."""
    privado.secret(con)
    latest = privado.latest(con, settings)
    if latest is None:
        return ["identidade sem snapshot: rode `dado-publico identity`"]
    return _differences(con, latest)
