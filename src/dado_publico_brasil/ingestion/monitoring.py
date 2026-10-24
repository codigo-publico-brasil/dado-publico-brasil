"""Monitoramento das fontes: a fonte respondeu? as colunas mudaram? o volume despencou?

Cada verificação grava uma linha em `metadata.source_checks` (status `ok`, `warn` ou `error`), que a
orquestração e a página de qualidade leem. Nada aqui interrompe a captura: o objetivo é saber que algo
quebrou, não parar o que ainda funciona. O frescor (idade do dado carregado) é medido pelo dbt.
"""

import json
from datetime import datetime
from pathlib import Path

from dado_publico_brasil.core import runs
from dado_publico_brasil.core.warehouse import Connection
from dado_publico_brasil.ingestion import read
from dado_publico_brasil.ingestion.contract import Dataset, SourceContract

VOLUME_DROP = 0.8  # menos de 80% das linhas da carga anterior vira aviso


def record(
    con: Connection,
    source: str,
    dataset: str,
    partition: int | None,
    check: str,
    status: str,
    detail: str = "",
) -> None:
    con.execute(
        "INSERT INTO metadata.source_checks "
        "(checked_at, source, dataset, partition, check_name, status, detail) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (runs.now(), source, dataset, partition, check, status, detail),
    )


def check_header(
    con: Connection, contract: SourceContract, dataset: Dataset, partition: int | None, file: Path
) -> None:
    """Compara os campos do arquivo com o contrato e com a captura anterior do mesmo dataset e partição.

    Coluna do contrato ausente é erro em CSV (o layout mudou) e aviso em JSON (a API omite campo vazio, então
    ausente quer dizer vazio no arquivo todo). Nome antigo declarado em `aliases` vale como a coluna atual. A
    mudança de colunas só se mede contra o mesmo arquivo capturado antes: um ano antigo ter menos campos que o
    seguinte é a natureza do dado, não alerta.
    """
    header = read.fields(file, contract, dataset)
    source, name = contract.source, dataset.name
    if not header:  # sem registros não há o que comparar (o volume é medido à parte)
        record(con, source, name, partition, "schema", "ok", "arquivo sem registros")
        return
    present = set(header) | {new for old, new in dataset.aliases.items() if old in header}
    missing = [c for c in dataset.columns if c not in present]
    previous = con.execute(
        "SELECT detail FROM metadata.source_checks WHERE source = ? AND dataset = ? "
        "AND partition IS NOT DISTINCT FROM ? AND check_name = 'header' ORDER BY id DESC LIMIT 1",
        (source, name, partition),
    ).fetchone()
    old = json.loads(previous[0]) if previous else None
    changed = old is not None and set(old) != set(header)
    if missing:
        severity = "warn" if contract.format_of(name) == "json" else "error"
        record(con, source, name, partition, "schema", severity, f"colunas do contrato ausentes: {missing}")
    if changed:
        added, removed = sorted(set(header) - set(old or [])), sorted(set(old or []) - set(header))
        detail = f"colunas novas: {added}; removidas: {removed}"
        record(con, source, name, partition, "schema_mudou", "warn", detail)
    if not missing:
        record(con, source, name, partition, "schema", "ok")
    if not changed:
        record(con, source, name, partition, "schema_mudou", "ok")
    if old is None or changed:
        record(con, source, name, partition, "header", "ok", json.dumps(header))


def check_volume(con: Connection, source: str, dataset: str, partition: int | None, rows: int) -> None:
    """Avisa se a carga trouxe muito menos linhas que a anterior do mesmo dataset e partição."""
    previous = con.execute(
        "SELECT rows_in FROM metadata.runs WHERE stage = 'load' AND source = ? AND dataset = ? "
        "AND year IS NOT DISTINCT FROM ? AND status = 'ok' ORDER BY id DESC LIMIT 1",
        (source, dataset, partition),
    ).fetchone()
    if previous and previous[0] and rows < VOLUME_DROP * previous[0]:
        record(con, source, dataset, partition, "volume", "warn", f"de {previous[0]} para {rows} linhas")
    else:
        record(con, source, dataset, partition, "volume", "ok", f"{rows} linhas")


def check_load(
    con: Connection, source: str, dataset: str, partition: int | None, stats: dict[str, int]
) -> None:
    """Registra o balanço da carga: o que foi lido, filtrado pelo `only`, carregado, rejeitado e em colisão.

    Linha rejeitada (sem valor na chave) e chave que junta linhas diferentes são perda de dado e valem erro. O
    filtro `only` da declaração fica no detalhe, para nunca ser invisível. Um registro por carga: o mais
    recente substitui o anterior no relatório.
    """
    lost = stats["rejected"] or stats["conflicting"]
    detail = (
        f"lidas {stats['read']}, filtradas pelo only {stats['filtered']}, carregadas {stats['loaded']}, "
        f"rejeitadas {stats['rejected']}, colisões de chave {stats['conflicting']}"
    )
    record(con, source, dataset, partition, "carga", "error" if lost else "ok", detail)


def errors_since(con: Connection, moment: datetime) -> int:
    """Quantas verificações com erro foram gravadas desde o momento dado."""
    row = con.execute(
        "SELECT COUNT(*) FROM metadata.source_checks WHERE status = 'error' AND checked_at >= ?",
        (moment.isoformat(timespec="seconds"),),
    ).fetchone()
    return int(row[0]) if row else 0
