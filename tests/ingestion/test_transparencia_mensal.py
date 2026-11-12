"""Meses fechados, mês ainda não publicado e pacote único lido por vários datasets (ADR 0045)."""

import zipfile
from datetime import date
from pathlib import Path

from dado_publico_brasil.core.settings import Settings
from dado_publico_brasil.core.warehouse import Connection
from dado_publico_brasil.ingestion import fetch, landing, monitoring
from dado_publico_brasil.ingestion.contract import SourceContract, load_contract
from dado_publico_brasil.ingestion.fetch import Downloader

HEADER = """
source: teste
power: executivo
level: federal
description: Fonte de teste
schedule: "0 6 * * *"
access: {base_url: "http://exemplo", delimiter: ",", encoding: utf-8}
datasets:
"""
DATASET = """  {name}:
    url: "{{base_url}}/{{month}}_{file}.zip{fragment}"
    load: yearly
    partition: month
    first_month: 202608
    lag_months: 1
    write: replace
    archive: zip
    columns: [codigo]
"""
TODAY = date(2026, 10, 24)


def contract(tmp_path: Path) -> SourceContract:
    parts = [
        DATASET.format(name="despesas", file="Despesas", fragment=""),
        DATASET.format(name="contratos", file="Compras", fragment="#contratos"),
        DATASET.format(name="itens", file="Compras", fragment="#itens"),
        DATASET.format(name="aditivos", file="Compras", fragment="#aditivos"),
    ]
    file = tmp_path / "contract.yml"
    file.write_text(HEADER + "".join(parts), encoding="utf-8")
    return load_contract(file)


def writing_downloader(gets: list[str], sha: str | None = None) -> Downloader:
    def downloader(url: str, folder: Path) -> tuple[Path, str, int]:
        gets.append(url)
        folder.mkdir(parents=True, exist_ok=True)
        file = folder / "arquivo.zip"
        with zipfile.ZipFile(file, "w") as package:
            package.writestr("dados.csv", "codigo\n1\n")
        return file, sha or f"h{url}", file.stat().st_size

    return downloader


def no_head(url: str) -> dict[str, str | None]:
    return {}


def test_only_closed_months_are_planned_and_the_daily_plan_asks_for_the_last_two_closed(
    tmp_path: Path,
) -> None:
    source = contract(tmp_path)
    assert landing.partitions(source.datasets["despesas"], {2026}, TODAY) == [202608, 202609]
    daily = [p for d, p in landing.plan_incremental(source, TODAY) if d == "despesas"]
    assert daily == [202608, 202609]  # o mês em curso (2026-10) não é pedido
    assert landing.current_partition(source.datasets["despesas"], date(2027, 1, 5)) == 202612


def test_a_403_on_the_latest_closed_month_is_not_yet_published_and_does_not_stop_the_source(
    con: Connection, tmp_path: Path, settings: Settings
) -> None:
    source = contract(tmp_path)
    latest = landing.current_partition(source.datasets["despesas"], date.today())
    gets: list[str] = []
    writer = writing_downloader(gets)

    def downloader(url: str, folder: Path) -> tuple[Path, str, int]:
        if f"{latest}_Despesas" in url:
            gets.append(url)
            raise fetch.SourceBlocked(f"{url}: HTTP 403", 403)
        return writer(url, folder)

    items: list[landing.Item] = [("despesas", latest), ("contratos", latest - 1)]
    assert landing.extract_plan(con, settings, source, items, downloader, no_head) == 2
    assert len(gets) == 2  # o segundo item é pedido
    status = monitoring.latest_status(con, "teste", "despesas")[1]
    assert not [d for d in status if "bloqueio" in d]
    assert con.execute(
        "SELECT count(*) FROM metadata.fontes_verificacoes "
        "WHERE verificacao = 'availability' AND tipo_ocorrencia = 'nao_publicado' AND cd_status_http = 403"
    ).fetchone() == (1,)


def test_a_403_on_an_older_month_is_still_a_block(
    con: Connection, tmp_path: Path, settings: Settings
) -> None:
    def blocked(url: str, folder: Path) -> tuple[Path, str, int]:
        raise fetch.SourceBlocked(f"{url}: HTTP 403", 403)

    source = contract(tmp_path)
    old = landing.current_partition(source.datasets["despesas"], date.today()) - 100  # um ano antes
    items: list[landing.Item] = [("despesas", old), ("despesas", old + 1)]
    assert landing.extract_plan(con, settings, source, items, blocked, no_head) == 0
    assert monitoring.latest_status(con, "teste", "despesas")[0] == "error"


def test_three_datasets_of_the_same_zip_cost_one_download_per_month(
    con: Connection, tmp_path: Path, settings: Settings
) -> None:
    gets: list[str] = []
    downloader = writing_downloader(gets, sha="sha-igual")

    def head(url: str) -> dict[str, str | None]:
        return {"etag": "e1", "last_modified": None, "size": None}

    source = contract(tmp_path)
    items: list[landing.Item] = [("contratos", 202609), ("itens", 202609), ("aditivos", 202609)]
    assert landing.extract_plan(con, settings, source, items, downloader, head) == 3
    assert len(gets) == 1
    found = con.execute("SELECT dataset, caminho, sha256 FROM metadata.capturas ORDER BY dataset").fetchall()
    assert [r[0] for r in found] == ["aditivos", "contratos", "itens"]
    assert len({r[1] for r in found}) == 1 and len({r[2] for r in found}) == 1
    # outro dia, nada mudou: nenhum download
    assert landing.extract_plan(con, settings, source, items, downloader, head) == 3
    assert len(gets) == 1
    # a fonte republica o mês: um download novo e os três datasets o recebem
    gets.clear()
    republished = writing_downloader(gets, sha="sha-novo")

    def head_new(url: str) -> dict[str, str | None]:
        return {"etag": "e2", "last_modified": None, "size": None}

    assert landing.extract_plan(con, settings, source, items, republished, head_new) == 3
    assert len(gets) == 1
    assert con.execute(
        "SELECT count(DISTINCT dataset) FROM metadata.capturas WHERE sha256 = 'sha-novo'"
    ).fetchone() == (3,)
