"""Loader: do landing (arquivos) para o raw (`raw_<fonte>.*`), com o dlt.

O raw é fiel à fonte: só as colunas permitidas pelo contrato, com o nome normalizado para
snake_case pelo dlt, valores como texto e vazio virando nulo. Nada é renomeado, convertido ou
limpo aqui; isso é trabalho do dbt (staging). Cada linha leva `_source_file_id`, o id da captura
(arquivo do landing) de onde veio. O dlt cria a tabela, evolui o esquema (coluna nova no contrato
aparece sozinha), faz `merge` pela chave natural (ou pelo conteúdo da linha, com `_row_hash`) e
registra cada carga (`_dlt_load_id`).
"""

import hashlib
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import dlt
from dlt.common.normalizers.naming.snake_case import NamingConvention
from dlt.extract import DltResource

from plataforma_dados.core import runs
from plataforma_dados.core.settings import Settings
from plataforma_dados.core.warehouse import Connection
from plataforma_dados.ingestion import landing, monitoring, read
from plataforma_dados.ingestion.contract import ROW_HASH, Dataset, SourceContract

normalize = NamingConvention().normalize_identifier


def _clean(value: Any) -> Any:
    """Vazio vira nulo; o resto fica como veio (listas seguem para o dlt, que cria as tabelas filhas)."""
    return None if value is None or (isinstance(value, str) and not value.strip()) else value


def read_rows(
    file: Path, contract: SourceContract, dataset: Dataset, file_id: int, stats: dict[str, int]
) -> Iterator[dict[str, Any]]:
    """Linhas do arquivo, só com as colunas permitidas. Linhas sem a chave são rejeitadas."""
    names = {column: normalize(column) for column in dataset.columns}
    key = [names.get(c, c) for c in dataset.primary_key]
    for record in read.records(file, contract, dataset):
        stats["read"] += 1
        row: dict[str, Any] = {names[c]: _clean(record.get(c)) for c in dataset.columns}
        row["_source_file_id"] = file_id
        if ROW_HASH in dataset.primary_key:
            joined = "".join(str(row[names[c]] or "") for c in dataset.columns)
            row[ROW_HASH] = hashlib.sha256(joined.encode()).hexdigest()
        if any(row[k] is None for k in key):
            stats["rejected"] += 1
            continue
        stats["loaded"] += 1
        yield row


def resource(
    file: Path, contract: SourceContract, dataset: Dataset, file_id: int, stats: dict[str, int]
) -> DltResource:
    key = [normalize(c) for c in dataset.primary_key]
    # Tudo texto (o dbt converte), assim a coluna existe mesmo que venha toda vazia; as listas (`nested`)
    # ficam sem tipo: o dlt cria as tabelas filhas.
    columns: dict[str, dict[str, Any]] = {
        normalize(c): {"data_type": "text", "nullable": normalize(c) not in key}
        for c in dataset.columns
        if c not in dataset.nested
    }
    if ROW_HASH in dataset.primary_key:
        columns[ROW_HASH] = {"data_type": "text", "nullable": False}
    columns["_source_file_id"] = {"data_type": "bigint", "nullable": False}
    return dlt.resource(  # type: ignore[call-overload,no-any-return]
        lambda: read_rows(file, contract, dataset, file_id, stats),
        name=normalize(dataset.name),
        write_disposition=dataset.write,
        primary_key=key or None,
        columns=columns,
    )


def pipeline(settings: Settings, contract: SourceContract, con: Connection | None = None) -> Any:
    """Pipeline do dlt para o esquema `raw_<fonte>`. O estado do dlt fica dentro do storage."""
    # A área temporária do dlt (merge/replace) ganha prefixo próprio para não parecer a camada staging do dbt.
    destination = dlt.destinations.duckdb(
        con if con is not None else str(settings.warehouse),
        staging_dataset_name_layout="dlt_tmp_%s",
    )
    return dlt.pipeline(
        pipeline_name=contract.schema,
        pipelines_dir=str(settings.state_dir / "dlt"),
        destination=destination,
        dataset_name=contract.schema,
    )


def load_file(
    settings: Settings,
    contract: SourceContract,
    dataset: Dataset,
    file: Path,
    file_id: int,
    con: Connection | None = None,
) -> dict[str, int]:
    """Carrega um arquivo no raw. Devolve as contagens (lidas, carregadas, rejeitadas)."""
    stats = {"read": 0, "loaded": 0, "rejected": 0}
    pipeline(settings, contract, con).run(resource(file, contract, dataset, file_id, stats))
    return stats


def load_capture(
    con: Connection, settings: Settings, contract: SourceContract, capture: dict[str, Any]
) -> int:
    """Carrega uma captura e a marca como carregada. Devolve as linhas carregadas."""
    dataset = contract.datasets[capture["dataset"]]
    with runs.track(con, "load", contract.source, dataset.name, capture["year"]) as run:
        stats = load_file(
            settings, contract, dataset, settings.storage_root / capture["path"], capture["id"], con
        )
        if not dataset.foreach:  # lotes têm tamanhos diferentes por natureza
            monitoring.check_volume(con, contract.source, dataset.name, capture["year"], stats["read"])
        run.rows_in, run.rows_out = stats["read"], stats["loaded"]
        con.execute("UPDATE metadata.captures SET loaded_at = ? WHERE id = ?", (runs.now(), capture["id"]))
        return stats["loaded"]


def load_pending(
    con: Connection, settings: Settings, contract: SourceContract, rebuild: bool = False
) -> tuple[int, int]:
    """Carrega as capturas vigentes ainda não carregadas (todas, com `rebuild`).

    Devolve (capturas carregadas, linhas carregadas).
    """
    captures = rows = 0
    for capture in landing.current_captures(con, contract.source):
        if capture["loaded_at"] is not None and not rebuild:
            continue
        rows += load_capture(con, settings, contract, capture)
        captures += 1
    return captures, rows
