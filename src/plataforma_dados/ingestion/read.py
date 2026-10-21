"""Ler: transformar o arquivo guardado no landing em registros (dicionários campo -> valor).

Um leitor por formato (`csv`, `json`). No JSON, `records` do dataset diz onde está a lista de registros
(caminho com pontos) e os objetos aninhados viram campos `a__b`; as listas ficam como estão e o dlt as
transforma em tabelas filhas. Uma fonte que precise de outro jeito (arquivo compactado, XML, layout fixo...)
define `records(file, dataset)` no módulo `custom` da fonte.
"""

import csv
import json
from collections.abc import Iterator
from itertools import islice
from pathlib import Path
from typing import Any

from plataforma_dados.ingestion.contract import Dataset, SourceContract

SAMPLE = 200  # registros olhados para listar os campos de um JSON


def _csv(file: Path, contract: SourceContract, dataset: Dataset) -> Iterator[dict[str, Any]]:
    with file.open(encoding=contract.encoding, newline="") as f:
        yield from csv.DictReader(f, delimiter=contract.delimiter)


def flatten(value: dict[str, Any], prefix: str = "") -> dict[str, Any]:
    flat: dict[str, Any] = {}
    for key, item in value.items():
        if isinstance(item, dict):
            flat.update(flatten(item, f"{prefix}{key}__"))
        else:
            flat[f"{prefix}{key}"] = item
    return flat


def _json(file: Path, contract: SourceContract, dataset: Dataset) -> Iterator[dict[str, Any]]:
    found: Any = json.loads(file.read_text(encoding=contract.encoding))
    for step in filter(None, (dataset.records or "").split(".")):
        found = found.get(step) if isinstance(found, dict) else None
    for item in found or []:
        yield flatten(item)


READERS = {"csv": _csv, "json": _json}


def records(file: Path, contract: SourceContract, dataset: Dataset) -> Iterator[dict[str, Any]]:
    custom = getattr(contract.custom, "records", None)
    return custom(file, dataset) if custom else READERS[contract.format](file, contract, dataset)


def fields(file: Path, contract: SourceContract, dataset: Dataset) -> list[str]:
    """Campos do arquivo: o cabeçalho do CSV ou a união dos campos dos primeiros registros do JSON."""
    if contract.format == "csv" and not contract.custom:
        with file.open(encoding=contract.encoding, newline="") as f:
            return next(csv.reader(f, delimiter=contract.delimiter), [])
    names: dict[str, None] = {}
    for record in islice(records(file, contract, dataset), SAMPLE):
        names.update(dict.fromkeys(record))
    # objeto nulo aparece como o próprio nome e, preenchido, como `nome__campo`: vale só o segundo
    return sorted(n for n in names if not any(o.startswith(n + "__") for o in names))
