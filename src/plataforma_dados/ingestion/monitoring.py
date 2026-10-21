"""Monitoramento das fontes: a fonte respondeu? as colunas mudaram? o volume despencou?

Cada verificação grava uma linha em `metadata.source_checks` (status `ok`, `warn` ou `error`), que a
orquestração e a página de qualidade leem. Nada aqui interrompe a captura: o objetivo é saber que algo
quebrou, não parar o que ainda funciona. O frescor (idade do dado carregado) é medido pelo dbt.
"""

import csv
import json
from datetime import datetime
from pathlib import Path

from plataforma_dados.core import runs
from plataforma_dados.core.warehouse import Connection
from plataforma_dados.ingestion.contract import Dataset, SourceContract

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
    """Compara as colunas do arquivo com o contrato e com o arquivo anterior do mesmo dataset."""
    with file.open(encoding=contract.encoding, newline="") as f:
        header = next(csv.reader(f, delimiter=contract.delimiter), [])
    source, name = contract.source, dataset.name
    missing = [c for c in dataset.columns if c not in header]
    previous = con.execute(
        "SELECT detail FROM metadata.source_checks "
        "WHERE source = ? AND dataset = ? AND check_name = 'header' ORDER BY id DESC LIMIT 1",
        (source, name),
    ).fetchone()
    old = json.loads(previous[0]) if previous else None
    changed = old is not None and old != header
    if missing:
        record(con, source, name, partition, "schema", "error", f"colunas do contrato ausentes: {missing}")
    if changed:
        added, removed = sorted(set(header) - set(old or [])), sorted(set(old or []) - set(header))
        record(
            con, source, name, partition, "schema", "warn", f"colunas novas: {added}; removidas: {removed}"
        )
    if not missing and not changed:
        record(con, source, name, partition, "schema", "ok")
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


def errors_since(con: Connection, moment: datetime) -> int:
    """Quantas verificações com erro foram gravadas desde o momento dado."""
    row = con.execute(
        "SELECT COUNT(*) FROM metadata.source_checks WHERE status = 'error' AND checked_at >= ?",
        (moment.isoformat(timespec="seconds"),),
    ).fetchone()
    return int(row[0]) if row else 0
