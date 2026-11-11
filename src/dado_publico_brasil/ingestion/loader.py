"""Loader: do landing (arquivos) para o raw (`raw_<fonte>.*`), com o dlt.

O raw é fiel à fonte: só as colunas permitidas pelo contrato, com o nome normalizado para
snake_case pelo dlt, valores como texto e vazio virando nulo. Nada é renomeado, convertido ou
limpo aqui; isso é trabalho do dbt (staging). Cada linha leva `_source_file_id`, o id da captura
(arquivo do landing) de onde veio, e `_ingested_at`, o instante em que chegou ao raw.

O raw é Parquet, uma pasta por captura (`<storage>/raw/<esquema>/<tabela>/<id_captura>/`), gravado pelo
destino `filesystem` do dlt (ADR 0051). A vigência é a presença da pasta: ao carregar uma captura, saem as
pastas das capturas que ela substitui (mesma URL), e o início do `load_pending` apaga o que não é vigente.
`raw_<fonte>.<tabela>` é uma view sobre os arquivos (`union_by_name`); no `merge`, ela fica com a última
captura de cada chave natural. O DuckDB é só o motor: não guarda o raw.
"""

import hashlib
import json
import logging
import os
import shutil
import time
from collections import Counter
from collections.abc import Callable, Iterator, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import dlt
import duckdb
from dlt.common.normalizers.naming.snake_case import NamingConvention
from dlt.extract import DltResource

from dado_publico_brasil.core import runs
from dado_publico_brasil.core.settings import Settings
from dado_publico_brasil.core.warehouse import Connection, replace_view
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
        # JSON: o limite entre colunas e o nulo ficam no texto (senão ("ab","c") e ("a","bc") colidem)
        digest = hashlib.sha256(
            json.dumps([row[names[c]] for c in dataset.columns], ensure_ascii=False, default=str).encode()
        ).hexdigest()
        if ROW_HASH in dataset.primary_key:
            # linhas idênticas no arquivo são todas da fonte: da segunda em diante o contador entra na chave
            repeats[digest] += 1
            row[ROW_HASH] = digest if repeats[digest] == 1 else f"{digest}:{repeats[digest]}"
        if any(row[k] is None for k in key):
            stats["rejected"] += 1
            continue
        # a chave natural tem de identificar a linha: mesma chave com conteúdo diferente é perda
        if natural_key and seen.setdefault(tuple(row[k] for k in key), digest) != digest:
            stats["conflicting"] += 1
        stats["loaded"] += 1
        yield row


def _hints(dataset: Dataset) -> dict[str, Any]:
    """Nome, chave, disposição e colunas do recurso do dlt."""
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
    columns["_ingested_at"] = {"data_type": "timestamp", "nullable": False}
    return {
        "name": normalize(dataset.name),
        # o dlt só acrescenta no filesystem: substituir é apagar a pasta da captura antiga, e o `merge` é a
        # view, que fica com a última captura de cada chave
        "write_disposition": "append",
        "primary_key": key or None,
        "columns": columns,
    }


def resource(
    file: Path,
    contract: SourceContract,
    dataset: Dataset,
    file_id: int,
    stats: dict[str, int],
    log: Log = default_log,
) -> DltResource:
    return dlt.resource(lambda: read_rows(file, contract, dataset, file_id, stats, log), **_hints(dataset))


def raw_dir(settings: Settings, contract: SourceContract) -> Path:
    """Pasta do raw da fonte: `<storage>/raw/<esquema>/<tabela>/<id_captura>/*.parquet`."""
    return settings.storage_root / "raw" / contract.schema


def pipeline(settings: Settings, contract: SourceContract, file_id: int = 0) -> Any:
    """Pipeline do dlt que grava a captura `file_id` em Parquet (zstd) na pasta dela (estado no storage)."""
    os.environ.setdefault("NORMALIZE__DATA_WRITER__COMPRESSION", "zstd")
    destination = dlt.destinations.filesystem(
        bucket_url=str(raw_dir(settings, contract).parent),  # o dlt acrescenta o `dataset_name` (o esquema)
        layout="{table_name}/{id_captura}/{load_id}.{file_id}.{ext}",
        extra_placeholders={"id_captura": str(file_id)},
    )
    return dlt.pipeline(
        pipeline_name=contract.schema,
        pipelines_dir=str(settings.state_dir / "dlt"),
        destination=destination,
        dataset_name=contract.schema,
    )


def _table_dirs(settings: Settings, contract: SourceContract) -> list[Path]:
    """Pastas de tabela do raw (as tabelas internas do dlt, `_dlt_*`, ficam de fora)."""
    root = raw_dir(settings, contract)
    return (
        [d for d in root.iterdir() if d.is_dir() and not d.name.startswith("_dlt_")] if root.is_dir() else []
    )


def _files(settings: Settings, contract: SourceContract, table: str, ids: Sequence[int]) -> list[str]:
    """Arquivos Parquet das capturas `ids` na tabela do raw."""
    folder = raw_dir(settings, contract) / table
    return [f.as_posix() for i in ids for f in sorted((folder / str(i)).glob("*.parquet"))]


def drop_captures(settings: Settings, contract: SourceContract, ids: Sequence[int]) -> None:
    """Apaga do raw as pastas das capturas `ids` (todas as tabelas, inclusive as filhas)."""
    for folder in _table_dirs(settings, contract):
        for i in ids:
            shutil.rmtree(folder / str(i), ignore_errors=True)


def drop_stale(settings: Settings, contract: SourceContract, keep: set[int]) -> None:
    """Apaga do raw as pastas de capturas fora de `keep`."""
    names = {str(i) for i in keep}
    for folder in _table_dirs(settings, contract):
        for capture in folder.iterdir():
            if capture.is_dir() and capture.name not in names:
                shutil.rmtree(capture, ignore_errors=True)


def _counts(
    settings: Settings, contract: SourceContract, dataset: Dataset, file_id: int, superseded: Sequence[int]
) -> tuple[int, int]:
    """(linhas das capturas substituídas, dessas as que a nova não traz pela chave)."""
    table = normalize(dataset.name)
    old = _files(settings, contract, table, superseded)
    if not old:
        return 0, 0
    new = _files(settings, contract, table, [file_id])
    keys = ", ".join(f'"{normalize(c)}"' for c in dataset.primary_key)
    con = duckdb.connect()
    try:
        row = con.execute("SELECT count(*) FROM read_parquet(?, union_by_name = true)", [old]).fetchone()
        total = int(row[0]) if row else 0
        if dataset.write != "merge":
            return total, 0
        if not new:
            return total, total
        row = con.execute(
            f"SELECT count(*) FROM read_parquet(?, union_by_name = true) WHERE ({keys}) NOT IN "
            f"(SELECT {keys} FROM read_parquet(?, union_by_name = true))",
            [old, new],
        ).fetchone()
        return total, int(row[0]) if row else 0
    finally:
        con.close()


def load_file(
    settings: Settings,
    contract: SourceContract,
    dataset: Dataset,
    file: Path,
    file_id: int,
    superseded: Sequence[int] = (),
    log: Log = default_log,
) -> dict[str, int]:
    """Carrega um arquivo no raw. Devolve as contagens: lidas, filtradas (`only`), carregadas, rejeitadas (sem
    chave), em colisão (mesma chave, conteúdo diferente), substituídas e removidas.

    `superseded` são os ids das versões anteriores do mesmo arquivo: depois da carga nova, suas pastas saem do
    raw (a vigência é a presença da pasta). `replaced` conta as linhas que saíram; `removed`, no `merge`, as
    que a captura nova não traz pela chave (a fonte as removeu ou, na chave por conteúdo, as alterou). A
    pasta da própria captura, se já estava lá por uma carga interrompida, sai antes."""
    stats = {
        "read": 0,
        "filtered": 0,
        "loaded": 0,
        "rejected": 0,
        "conflicting": 0,
        "replaced": 0,
        "removed": 0,
    }
    p = pipeline(settings, contract, file_id)
    drop_captures(settings, contract, [file_id])
    started = time.monotonic()
    log(f"{contract.source}.{dataset.name}: carga de {file.name} ({file.stat().st_size / 2**20:,.0f} MB)")
    try:
        p.run(resource(file, contract, dataset, file_id, stats, log), loader_file_format="parquet")
    except Exception:
        p.drop_pending_packages()  # o pacote da carga que falhou não trava a próxima; o landing refaz
        drop_captures(settings, contract, [file_id])
        raise
    stats["replaced"], stats["removed"] = _counts(settings, contract, dataset, file_id, superseded)
    drop_captures(settings, contract, superseded)
    log(
        f"{contract.source}.{dataset.name}: {stats['loaded']:,} linhas carregadas de {stats['read']:,} lidas "
        f"({stats['replaced']:,} de versões anteriores substituídas) em {time.monotonic() - started:,.0f}s"
    )
    return stats


def reset_dataset(
    settings: Settings, contract: SourceContract, dataset: Dataset, con: Connection | None = None
) -> None:
    """Apaga o raw do dataset (e das filhas), para recarregar do zero do landing, que não é tocado.

    Necessário quando o contrato muda a chave primária. Com `con`, apaga também a tabela nativa do raw
    anterior ao ADR 0051 (a view toma o lugar dela na próxima carga)."""
    name = normalize(dataset.name)
    for folder in _table_dirs(settings, contract):
        if folder.name == name or folder.name.startswith(f"{name}__"):
            shutil.rmtree(folder, ignore_errors=True)
    if con is not None:
        for (table,) in con.execute(
            "SELECT table_name FROM duckdb_tables() WHERE schema_name = ? "
            "AND (table_name = ? OR starts_with(table_name, ?))",
            (contract.schema, name, f"{name}__"),
        ).fetchall():
            con.execute(f'DROP TABLE "{contract.schema}"."{table}"')


_SQL_TYPES = {"text": "VARCHAR", "bigint": "BIGINT", "timestamp": "TIMESTAMPTZ"}


def _view_sql(
    settings: Settings, contract: SourceContract, dataset: Dataset, table: str, parent: str | None
) -> str:
    """SELECT da view do raw. No `merge`, a tabela do dataset fica com a última captura de cada chave e a
    filha, com as linhas cuja pai ficou (`parent` é a pai da filha, outra view)."""
    folder = raw_dir(settings, contract) / table
    if not any(folder.glob("*/*.parquet")):  # dataset sem captura: view vazia, tipada pelo contrato
        columns = {
            **_hints(dataset)["columns"],
            "_dlt_load_id": {"data_type": "text"},
            "_dlt_id": {"data_type": "text"},
        }
        cast = ", ".join(f'NULL::{_SQL_TYPES[c["data_type"]]} AS "{n}"' for n, c in columns.items())
        return f"SELECT {cast} WHERE false"
    source = f"'{folder.as_posix().replace(chr(39), chr(39) * 2)}/*/*.parquet', union_by_name = true"
    if dataset.write != "merge":
        return f"SELECT * FROM read_parquet({source})"
    if parent:
        return (
            f"SELECT * FROM read_parquet({source}) WHERE _dlt_parent_id IN "
            f'(SELECT _dlt_id FROM "{contract.schema}"."{parent}")'
        )
    keys = ", ".join(f'"{normalize(c)}"' for c in dataset.primary_key)
    return (  # chave repetida na mesma captura: fica a primeira linha do arquivo (a colisão é contada)
        f"SELECT * EXCLUDE (filename, file_row_number) FROM read_parquet({source}, filename = true, "
        f"file_row_number = true) QUALIFY row_number() OVER (PARTITION BY {keys} "
        "ORDER BY _source_file_id DESC, filename, file_row_number) = 1"
    )


def create_views(
    settings: Settings, contract: SourceContract, con: Connection, log: Log = default_log
) -> None:
    """Cria (ou refaz) `raw_<esfera>_<fonte>.<tabela>` como view sobre o Parquet, de todo dataset `raw: true`,
    mesmo sem captura (view vazia): os modelos do dbt rodam com zero linhas e os testes medem a lacuna.

    As tabelas filhas (`<dataset>__<campo>`) saem das pastas que o dlt criou. As descrições das views
    sobrevivem à refeita. Tabela nativa do raw anterior ao ADR 0051 fica como está até o `load --rebuild`."""
    con.execute(f'CREATE SCHEMA IF NOT EXISTS "{contract.schema}"')
    on_disk = {d.name for d in _table_dirs(settings, contract)}
    wanted: set[str] = set()
    for dataset in contract.datasets.values():
        if not dataset.raw:
            continue
        name = normalize(dataset.name)
        family = sorted({name} | {t for t in on_disk if t.startswith(f"{name}__")}, key=len)
        for table in family:
            # a pai é a mais longa da família que prefixa o nome (o dlt omite o nível que é só um objeto)
            parent = max((t for t in family if table.startswith(f"{t}__")), key=len, default=None)
            if con.execute(
                "SELECT 1 FROM duckdb_tables() WHERE schema_name = ? AND table_name = ?",
                (contract.schema, table),
            ).fetchone():
                log(f"{contract.source}.{table}: ainda é tabela nativa; `load --rebuild` a troca pela view")
                continue
            replace_view(con, contract.schema, table, _view_sql(settings, contract, dataset, table, parent))
            wanted.add(table)
    for (view,) in con.execute(
        "SELECT view_name FROM duckdb_views() WHERE schema_name = ? AND NOT internal", (contract.schema,)
    ).fetchall():
        if view not in wanted:  # filha que não tem mais pasta
            con.execute(f'DROP VIEW "{contract.schema}"."{view}"')


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
        superseded = [
            r[0]
            for r in con.execute(
                "SELECT id_captura FROM metadata.capturas "
                "WHERE fonte = ? AND dataset = ? AND url = ? AND id_captura <> ?",
                (contract.source, dataset.name, capture["url"], capture["id_captura"]),
            ).fetchall()
        ]
        stats = load_file(
            settings,
            contract,
            dataset,
            settings.storage_root / capture["caminho"],
            capture["id_captura"],
            superseded,
            log,
        )
        monitoring.check_load(
            con,
            contract.source,
            dataset.name,
            capture["particao"],
            stats,
            dataset.rejeitadas_toleradas.get(capture["particao"]),
        )
        if not dataset.foreach:  # lotes têm tamanhos diferentes por natureza
            monitoring.check_volume(con, contract.source, dataset.name, capture["particao"], stats["read"])
            if dataset.write == "merge" and superseded:  # em `replace_partition` a foto nova é a completa
                monitoring.check_removed(
                    con, contract.source, dataset.name, capture["particao"], stats["removed"]
                )
        run.rows_in, run.rows_out = stats["read"], stats["loaded"]
        con.execute(
            "UPDATE metadata.capturas SET dt_carga = ? WHERE id_captura = ?",
            (runs.now(), capture["id_captura"]),
        )
        return stats["loaded"]


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


def _table_columns(con: Connection, contract: SourceContract, dataset: Dataset) -> set[str]:
    """Colunas da tabela (ou view) do dataset no raw (vazio se não existe)."""
    found = con.execute(
        "SELECT column_name FROM duckdb_columns() WHERE schema_name = ? AND table_name = ?",
        (contract.schema, normalize(dataset.name)),
    ).fetchall()
    return {r[0] for r in found}


def _failed(
    con: Connection,
    contract: SourceContract,
    dataset: str,
    partition: int | None,
    action: str,
    error: Exception,
    log: Log,
) -> None:
    """Registra a falha de um dataset em `metadata.fontes_verificacoes` (erro visível); os outros seguem."""
    detail = f"falha ao {action}: {type(error).__name__}: {str(error)[:500]}"
    monitoring.record(con, contract.source, dataset, partition, "carga", "error", detail)
    log(f"{contract.source}.{dataset}: {detail}")


def load_pending(
    con: Connection,
    settings: Settings,
    contract: SourceContract,
    rebuild: bool = False,
    only_dataset: str | None = None,
    log: Log = default_log,
) -> tuple[int, int]:
    """Carrega as capturas vigentes não carregadas (todas com `rebuild`; um dataset com `only_dataset`).

    Antes, apaga do raw as pastas de capturas que o landing não tem mais como vigentes (a última carregada de
    cada URL fica até a nova entrar). Raw que não tem uma coluna da chave do contrato (a chave mudou, por
    exemplo para `_row_hash`) é apagado e recarregado do landing, e a recarga fica em `fontes_verificacoes`.
    No fim, refaz as views (dataset sem captura ganha view vazia). Um dataset que falha é registrado (erro em
    `fontes_verificacoes`) e os demais seguem.

    Devolve (capturas carregadas, linhas carregadas).
    """
    captures = rows = 0
    reset: set[str] = set()  # datasets recarregados do zero (todas as capturas vigentes entram)
    failed: set[str] = set()
    current = landing.current_captures(con, contract.source)
    keep = {c["id_captura"] for c in current} | {
        r[0]
        for r in con.execute(
            "SELECT max(id_captura) FROM metadata.capturas WHERE fonte = ? AND dt_carga IS NOT NULL "
            "GROUP BY dataset, url",
            (contract.source,),
        ).fetchall()
    }
    drop_stale(settings, contract, keep)
    for name, dataset in contract.datasets.items():
        found = _table_columns(con, contract, dataset)
        lacking = [c for c in map(normalize, dataset.primary_key) if c not in found]
        if dataset.raw and found and lacking and only_dataset in (None, name):
            detail = (
                f"a tabela não tem a coluna da chave ({', '.join(lacking)}): apagada e recarregada do landing"
            )
            monitoring.record(con, contract.source, name, None, "recarga_por_chave", "ok", detail)
            log(f"{contract.source}.{name}: {detail}")
            reset_dataset(settings, contract, dataset, con)
            reset.add(name)
    for capture in current:
        name = capture["dataset"]
        if only_dataset not in (None, name) or not contract.datasets[name].raw or name in failed:
            continue
        if capture["dt_carga"] is not None and not rebuild and name not in reset:
            continue
        try:
            if rebuild and name not in reset:
                reset.add(name)
                reset_dataset(settings, contract, contract.datasets[name], con)
            rows += load_capture(con, settings, contract, capture, log)
            captures += 1
        except Exception as error:
            failed.add(name)
            _failed(con, contract, name, capture["particao"], f"carregar {capture['caminho']}", error, log)
    create_views(settings, contract, con, log)
    log(f"{contract.source}: {captures} capturas e {rows:,} linhas carregadas no raw")
    return captures, rows
