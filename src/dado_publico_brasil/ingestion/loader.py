"""Loader: do landing (arquivos) para o raw (`raw_<fonte>.*`), com o dlt.

O raw é fiel à fonte: só as colunas permitidas pelo contrato, com o nome normalizado para
snake_case pelo dlt, valores como texto e vazio virando nulo. Nada é renomeado, convertido ou
limpo aqui; isso é trabalho do dbt (staging). Cada linha leva `_source_file_id`, o id da captura
(arquivo do landing) de onde veio, e `_ingested_at`, o instante em que chegou ao raw. O dlt cria a tabela,
evolui o esquema (coluna nova no contrato
aparece sozinha), faz `merge` pela chave natural (ou pelo conteúdo da linha, com `_row_hash`), ou
`replace_partition` (arquivo que é a foto completa: saem as linhas das versões anteriores; ADR 0043),
e registra cada carga (`_dlt_load_id`). A carga usa o formato Parquet do dlt (ADR 0043).
"""

import hashlib
import logging
import time
from collections import Counter
from collections.abc import Callable, Iterator, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import dlt
from dlt.common.normalizers.naming.snake_case import NamingConvention
from dlt.extract import DltResource
from dlt.pipeline.helpers import pipeline_drop

from dado_publico_brasil.core import runs
from dado_publico_brasil.core.settings import Settings
from dado_publico_brasil.core.warehouse import Connection
from dado_publico_brasil.ingestion import landing, monitoring, read
from dado_publico_brasil.ingestion.contract import ROW_HASH, Dataset, SourceContract

normalize = NamingConvention().normalize_identifier

Log = Callable[[str], None]
PROGRESS_SECONDS = 30  # intervalo do aviso de progresso em cargas longas


def default_log(message: str) -> None:
    """Destino padrão dos avisos; o Dagster passa `context.log.info` para aparecerem na aba Runs."""
    logging.getLogger(__name__).info(message)


def _clean(value: Any) -> Any:
    """Vazio vira nulo; o resto fica como veio (listas seguem para o dlt, que cria as tabelas filhas)."""
    return None if value is None or (isinstance(value, str) and not value.strip()) else value


def read_rows(
    file: Path,
    contract: SourceContract,
    dataset: Dataset,
    file_id: int,
    stats: dict[str, int],
    log: Log = default_log,
) -> Iterator[dict[str, Any]]:
    """Linhas do arquivo, só com as colunas permitidas. Linhas sem a chave são rejeitadas."""
    names = {column: normalize(column) for column in dataset.columns}
    legacy = {new: old for old, new in dataset.aliases.items()}  # nome atual -> nome no layout antigo
    key = [names.get(c, c) for c in dataset.primary_key]
    natural_key = bool(key) and ROW_HASH not in dataset.primary_key
    ingested_at = datetime.now(UTC)  # o mesmo instante para o arquivo todo
    seen: dict[tuple[Any, ...], str] = {}  # chave natural -> conteúdo da linha, para achar colisões
    repeats: Counter[str] = Counter()
    last = time.monotonic()
    for record in read.records(file, contract, dataset):
        stats["read"] += 1
        if stats["read"] % 50_000 == 0 and time.monotonic() - last >= PROGRESS_SECONDS:
            last = time.monotonic()
            log(f"{dataset.name}: {stats['read']:,} linhas lidas de {file.name}")
        if any(record.get(field) not in allowed for field, allowed in dataset.only.items()):
            stats["filtered"] += 1
            continue  # minimização: fora do que a declaração diz que interessa
        row: dict[str, Any] = {
            names[c]: _clean(record.get(c) if c in record else record.get(legacy.get(c, c)))
            for c in dataset.columns
        }
        row["_source_file_id"] = file_id
        row["_ingested_at"] = ingested_at
        digest = hashlib.sha256(
            "".join(str(row[names[c]] or "") for c in dataset.columns).encode()
        ).hexdigest()
        if ROW_HASH in dataset.primary_key:
            # linhas idênticas no arquivo são todas da fonte: da segunda em diante o contador entra na chave
            repeats[digest] += 1
            row[ROW_HASH] = digest if repeats[digest] == 1 else f"{digest}:{repeats[digest]}"
        if any(row[k] is None for k in key):
            stats["rejected"] += 1
            continue
        if (
            natural_key
        ):  # a chave natural tem de identificar a linha: mesma chave com conteúdo diferente é perda
            if seen.setdefault(tuple(row[k] for k in key), digest) != digest:
                stats["conflicting"] += 1
        stats["loaded"] += 1
        yield row


def resource(
    file: Path,
    contract: SourceContract,
    dataset: Dataset,
    file_id: int,
    stats: dict[str, int],
    log: Log = default_log,
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
    columns["_ingested_at"] = {
        "data_type": "timestamp",
        "nullable": True,
    }  # nulo só se o preenchimento retroativo faltar
    return dlt.resource(  # type: ignore[call-overload,no-any-return]
        lambda: read_rows(file, contract, dataset, file_id, stats, log),
        name=normalize(dataset.name),
        # replace_partition: o dlt só acrescenta; as linhas das versões antigas saem em `load_file`
        write_disposition="append" if dataset.write == "replace_partition" else dataset.write,
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


def _delete_rows(p: Any, table: str, file_ids: Sequence[int]) -> int:
    """Apaga do raw as linhas vindas dos arquivos (capturas) dados; devolve quantas saíram."""
    if not file_ids:
        return 0
    marks = ", ".join("?" for _ in file_ids)
    with p.sql_client() as client:
        found = client.execute_sql(
            "SELECT count(*) FROM information_schema.tables WHERE table_schema = ? AND table_name = ?",
            p.dataset_name,
            table,
        )
        if not found[0][0]:
            return 0
        name = client.make_qualified_table_name(table)
        n = client.execute_sql(f"SELECT count(*) FROM {name} WHERE _source_file_id IN ({marks})", *file_ids)
        client.execute_sql(f"DELETE FROM {name} WHERE _source_file_id IN ({marks})", *file_ids)
        return int(n[0][0])


def load_file(
    settings: Settings,
    contract: SourceContract,
    dataset: Dataset,
    file: Path,
    file_id: int,
    con: Connection | None = None,
    superseded: Sequence[int] = (),
    log: Log = default_log,
) -> dict[str, int]:
    """Carrega um arquivo no raw. Devolve as contagens: lidas, filtradas (`only`), carregadas, rejeitadas (sem
    chave), em colisão (mesma chave, conteúdo diferente) e substituídas.

    `superseded` são os ids das versões anteriores do mesmo arquivo: em `write: replace_partition` suas linhas
    saem do raw depois da carga nova (a atual, se já estava lá por uma carga interrompida, sai antes)."""
    stats = {"read": 0, "filtered": 0, "loaded": 0, "rejected": 0, "conflicting": 0, "replaced": 0}
    p = pipeline(settings, contract, con)
    table = normalize(dataset.name)
    swap = dataset.write == "replace_partition"
    if swap:
        _delete_rows(p, table, [file_id])
    started = time.monotonic()
    log(f"{contract.source}.{dataset.name}: carga de {file.name} ({file.stat().st_size / 2**20:,.0f} MB)")
    p.run(resource(file, contract, dataset, file_id, stats, log), loader_file_format="parquet")
    if swap:
        stats["replaced"] = _delete_rows(p, table, superseded)
    log(
        f"{contract.source}.{dataset.name}: {stats['loaded']:,} linhas carregadas de {stats['read']:,} lidas "
        f"({stats['replaced']:,} de versões anteriores substituídas) em {time.monotonic() - started:,.0f}s"
    )
    return stats


def reset_dataset(
    settings: Settings, contract: SourceContract, dataset: Dataset, con: Connection | None = None
) -> None:
    """Descarta a tabela raw do dataset (e as tabelas filhas) e o estado do dlt, para recarregar do zero.

    Necessário quando o contrato muda a chave primária: o dlt não acrescenta uma coluna de chave a uma tabela
    que já existe. O landing não é tocado; a tabela é refeita pelos arquivos dele."""
    name = normalize(dataset.name)
    p = pipeline(settings, contract, con)
    if p.default_schema_name and name in p.default_schema.tables:
        pipeline_drop(p, resources=[name])()


def load_capture(
    con: Connection,
    settings: Settings,
    contract: SourceContract,
    capture: dict[str, Any],
    log: Log = default_log,
) -> int:
    """Carrega uma captura e a marca como carregada. Devolve as linhas carregadas."""
    dataset = contract.datasets[capture["dataset"]]
    with runs.track(con, "load", contract.source, dataset.name, capture["particao"]) as run:
        stats = load_file(
            settings,
            contract,
            dataset,
            settings.storage_root / capture["caminho"],
            capture["id_captura"],
            con,
            [
                r[0]
                for r in con.execute(
                    "SELECT id_captura FROM metadata.capturas "
                    "WHERE fonte = ? AND dataset = ? AND url = ? AND id_captura <> ?",
                    (contract.source, dataset.name, capture["url"], capture["id_captura"]),
                ).fetchall()
            ],
            log,
        )
        monitoring.check_load(con, contract.source, dataset.name, capture["particao"], stats)
        if not dataset.foreach:  # lotes têm tamanhos diferentes por natureza
            monitoring.check_volume(con, contract.source, dataset.name, capture["particao"], stats["read"])
            table = f"{contract.schema}.{normalize(dataset.name)}"
            if dataset.write != "replace_partition":  # lá, as linhas antigas já saíram
                monitoring.check_removed(
                    con, contract.source, dataset.name, capture["particao"], table, capture
                )
        run.rows_in, run.rows_out = stats["read"], stats["loaded"]
        con.execute(
            "UPDATE metadata.capturas SET dt_carga = ? WHERE id_captura = ?",
            (runs.now(), capture["id_captura"]),
        )
        return stats["loaded"]


def backfill_ingested_at(con: Connection, contract: SourceContract) -> int:
    """Cria `_ingested_at` nas tabelas do raw que ainda não a têm e preenche as linhas antigas com a data da
    carga do arquivo de origem (`metadata.capturas.dt_carga`). Devolve as linhas preenchidas."""
    filled = 0
    for dataset in contract.datasets.values():
        table = f"{contract.schema}.{normalize(dataset.name)}"
        if (
            not dataset.raw
            or not con.execute(
                "SELECT 1 FROM duckdb_tables() WHERE schema_name = ? AND table_name = ?",
                (contract.schema, normalize(dataset.name)),
            ).fetchone()
        ):
            continue
        con.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS _ingested_at TIMESTAMP WITH TIME ZONE")
        n = con.execute(f"SELECT count(*) FROM {table} WHERE _ingested_at IS NULL").fetchone()
        con.execute(
            f"UPDATE {table} AS t SET _ingested_at = (c.dt_carga AT TIME ZONE 'UTC') FROM metadata.capturas "
            f"AS c "
            "WHERE c.id_captura = t._source_file_id AND t._ingested_at IS NULL"
        )
        filled += int(n[0]) if n else 0
    return filled


def recheck_headers(con: Connection, settings: Settings, contract: SourceContract) -> int:
    """Refaz a checagem de cabeçalho dos arquivos vigentes do landing, sem baixar nada (por exemplo, depois de
    mudar o contrato). Devolve quantos arquivos foram conferidos."""
    n = 0
    for capture in landing.current_captures(con, contract.source):
        dataset = contract.datasets[capture["dataset"]]
        if dataset.raw and not dataset.foreach:
            monitoring.check_header(
                con, contract, dataset, capture["particao"], settings.storage_root / capture["caminho"]
            )
            n += 1
    return n


def load_pending(
    con: Connection,
    settings: Settings,
    contract: SourceContract,
    rebuild: bool = False,
    only_dataset: str | None = None,
    log: Log = default_log,
) -> tuple[int, int]:
    """Carrega as capturas vigentes não carregadas (todas com `rebuild`; um dataset com `only_dataset`).

    Devolve (capturas carregadas, linhas carregadas).
    """
    captures = rows = 0
    reset: set[str] = set()
    for capture in landing.current_captures(con, contract.source):
        if only_dataset not in (None, capture["dataset"]) or not contract.datasets[capture["dataset"]].raw:
            continue
        if capture["dt_carga"] is not None and not rebuild:
            continue
        if rebuild and capture["dataset"] not in reset:
            reset.add(capture["dataset"])
            reset_dataset(settings, contract, contract.datasets[capture["dataset"]], con)
        rows += load_capture(con, settings, contract, capture, log)
        captures += 1
    log(f"{contract.source}: {captures} capturas e {rows:,} linhas carregadas no raw")
    return captures, rows
