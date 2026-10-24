"""Ler: transformar o arquivo guardado no landing em registros (dicionários campo -> valor).

Um leitor por formato (`csv`, `json`). No JSON, `records` do dataset diz onde está a lista de registros
(caminho com pontos) e os objetos aninhados viram campos `a__b`; as listas ficam como estão e o dlt as
transforma em tabelas filhas. Uma fonte que precise de outro jeito (arquivo compactado, XML, layout fixo...)
define `records(file, dataset)` no módulo `custom` da fonte.
"""

import csv
import fnmatch
import io
import json
import zipfile
from collections.abc import Iterator
from itertools import islice
from pathlib import Path
from typing import Any

from dado_publico_brasil.ingestion import batch
from dado_publico_brasil.ingestion.contract import ITEM, Dataset, SourceContract

SAMPLE = 200  # registros olhados para listar os campos de um JSON


def _csv(file: Path, contract: SourceContract, dataset: Dataset) -> Iterator[dict[str, Any]]:
    if dataset.archive == "zip":  # lê o membro direto do pacote, sem extrair
        with zipfile.ZipFile(file) as package:
            for info in package.infolist():
                if fnmatch.fnmatch(info.filename, dataset.member):
                    with package.open(info) as member:
                        text = io.TextIOWrapper(member, encoding=contract.encoding, newline="")
                        yield from csv.DictReader(text, delimiter=contract.delimiter)
        return
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


def _select(found: Any, path: str | None) -> list[Any]:
    """A lista de registros: segue o caminho (com pontos) e aceita um objeto só como lista de um."""
    for step in filter(None, (path or "").split(".")):
        found = found.get(step) if isinstance(found, dict) else None
    return [found] if isinstance(found, dict) else (found or [])


def _json(file: Path, contract: SourceContract, dataset: Dataset) -> Iterator[dict[str, Any]]:
    for item in _select(json.loads(file.read_text(encoding=contract.encoding)), dataset.records):
        yield flatten(item)


def _batch(file: Path, contract: SourceContract, dataset: Dataset) -> Iterator[dict[str, Any]]:
    """Lote de um dataset por item: só as respostas 200 dão registros, cada um com o `_item` de origem."""
    for found in batch.read(file):
        if found["status"] == 200:
            for item in _select(json.loads(batch.body(found)), dataset.records):
                yield {**flatten(item), ITEM: found["item"]}


READERS = {"csv": _csv, "json": _json}


def records(file: Path, contract: SourceContract, dataset: Dataset) -> Iterator[dict[str, Any]]:
    custom = getattr(contract.custom, "records", None)
    if custom:
        return custom(file, dataset)  # type: ignore[no-any-return]
    if dataset.foreach:
        return _batch(file, contract, dataset)
    return READERS[contract.format_of(dataset.name)](file, contract, dataset)


def fields(file: Path, contract: SourceContract, dataset: Dataset) -> list[str]:
    """Campos do arquivo: o cabeçalho do CSV ou a união dos campos dos primeiros registros do JSON."""
    plain_csv = contract.format_of(dataset.name) == "csv" and not dataset.archive
    if plain_csv and not contract.custom and not dataset.foreach:
        with file.open(encoding=contract.encoding, newline="") as f:
            return next(csv.reader(f, delimiter=contract.delimiter), [])
    names: dict[str, None] = {}
    for record in islice(records(file, contract, dataset), SAMPLE):
        names.update(dict.fromkeys(record))
    # objeto nulo aparece como o próprio nome e, preenchido, como `nome__campo`: vale só o segundo
    return sorted(n for n in names if not any(o.startswith(n + "__") for o in names))
