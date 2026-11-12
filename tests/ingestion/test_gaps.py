"""Lacunas de partição e recuperação depois de uma pausa (issues 53 e 54)."""

from datetime import date
from pathlib import Path

from dado_publico_brasil.core import runs
from dado_publico_brasil.core.settings import Settings
from dado_publico_brasil.core.warehouse import Connection
from dado_publico_brasil.ingestion import fetch, landing, monitoring
from dado_publico_brasil.ingestion.contract import SourceContract, load_contract

CONTRACT = """
source: teste
power: legislativo
level: federal
description: Fonte de teste
schedule: "0 6 * * *"
access: {base_url: "http://exemplo", delimiter: ",", encoding: utf-8}
datasets:
  votos:
    url: "{base_url}/votos-{year}.csv"
    load: yearly
    first_year: 2020
    write: replace
    columns: [codigo]
  mensal:
    url: "{base_url}/mes-{year}.zip"
    load: yearly
    partition: month
    first_month: 202608
    archive: zip
    raw: false
  fotos:
    url: "{base_url}/fotos-{year}.zip"
    load: yearly
    first_year: 2020
    on_demand: true
    write: replace
    columns: [codigo]
  completo:
    url: "{base_url}/completo.csv"
    load: full
    write: replace
    columns: [codigo]
"""
TODAY = date(2026, 10, 24)


def contract(tmp_path: Path, schedule: bool = True) -> SourceContract:
    file = tmp_path / "contract.yml"
    text = CONTRACT if schedule else CONTRACT.replace('schedule: "0 6 * * *"\n', "")
    file.write_text(text, encoding="utf-8")
    return load_contract(file)


def captured(con: Connection, dataset: str, year: int) -> None:
    with runs.track(con, "extract", "teste", dataset, year) as run:
        landing.register_capture(
            con, "teste", dataset, year, f"http://exemplo/{dataset}-{year}", f"h{year}", 1, "x", run.id
        )


def test_gaps_list_expected_captured_and_missing_per_partition(con: Connection, tmp_path: Path) -> None:
    captured(con, "votos", 2020)
    captured(con, "votos", 2024)
    gaps = landing.partition_gaps(con, contract(tmp_path), TODAY)
    assert gaps["votos"] == {
        "esperadas": 7,
        "capturadas": 2,
        "indisponiveis": [],
        "faltam": [2021, 2022, 2023, 2025, 2026],
        "sob_demanda": False,
    }
    assert gaps["mensal"]["faltam"] == [202608, 202609, 202610]
    assert "completo" not in gaps  # dataset sem partição não tem lacuna de partição


def test_recovery_plans_only_what_is_missing_most_recent_first_up_to_the_limit(
    con: Connection, tmp_path: Path
) -> None:
    captured(con, "votos", 2020)
    captured(con, "votos", 2026)
    items = landing.plan_recovery(con, contract(tmp_path), TODAY, limit=2)
    assert [i for i in items if i[0] == "votos"] == [("votos", 2025), ("votos", 2024)]
    # o mês em curso fica com o plano incremental; aqui só os fechados que faltam
    assert [i for i in items if i[0] == "mensal"] == [("mensal", 202609), ("mensal", 202608)]


def test_a_partition_the_source_does_not_publish_is_unavailable_and_not_retried_forever(
    con: Connection, tmp_path: Path
) -> None:
    captured(con, "votos", 2020)
    monitoring.record(
        con, "teste", "votos", 2022, "availability", "error", cd_status_http=404, tipo="nao_encontrado"
    )
    monitoring.record(con, "teste", "votos", 2023, "availability", "error", "timed out", tipo="falha_de_rede")
    monitoring.record(
        con, "teste", "votos", 2024, "availability", "error", "HTTP Error 404: Not Found"
    )  # só texto
    gaps = landing.partition_gaps(con, contract(tmp_path), TODAY)["votos"]
    assert gaps["indisponiveis"] == [2022]  # o texto do detalhe não decide: só as colunas próprias
    assert 2022 not in gaps["faltam"] and 2023 in gaps["faltam"] and 2024 in gaps["faltam"]
    assert ("votos", 2022) not in landing.plan_recovery(con, contract(tmp_path), TODAY, limit=10)


def test_a_source_without_schedule_never_recovers_by_itself(con: Connection, tmp_path: Path) -> None:
    assert landing.plan_recovery(con, contract(tmp_path, schedule=False), TODAY) == []


def test_a_partition_that_arrives_stops_being_a_gap(con: Connection, tmp_path: Path) -> None:
    assert 2022 in landing.partition_gaps(con, contract(tmp_path), TODAY)["votos"]["faltam"]
    captured(con, "votos", 2022)
    assert 2022 not in landing.partition_gaps(con, contract(tmp_path), TODAY)["votos"]["faltam"]


def test_extract_plan_records_the_state_of_the_partitions_for_the_observability(
    con: Connection, tmp_path: Path, settings: Settings
) -> None:
    captured(con, "votos", 2020)
    landing.record_gaps(con, contract(tmp_path))
    row = con.execute(
        "SELECT resultado, detalhe FROM metadata.fontes_verificacoes WHERE verificacao = 'particoes' AND dataset = 'votos'"
    ).fetchone()
    assert row is not None and row[0] == "warn" and "1 de" in row[1] and "faltam:" in row[1]


def test_the_monthly_incremental_plan_asks_for_the_current_and_the_previous_month(tmp_path: Path) -> None:
    def mensal(today: date) -> list[int | None]:
        return [p for d, p in landing.plan_incremental(contract(tmp_path), today) if d == "mensal"]

    assert mensal(TODAY) == [202609, 202610]
    assert mensal(date(2027, 1, 2)) == [202612, 202701]  # a virada do ano pede o dezembro anterior
    assert landing.previous_month(202701) == 202612


def test_a_404_of_the_previous_month_at_the_turn_of_the_month_is_not_unavailable(
    con: Connection, tmp_path: Path
) -> None:
    for month in (202610, 202609):
        monitoring.record(
            con, "teste", "mensal", month, "availability", "error", cd_status_http=404, tipo="nao_encontrado"
        )
    gaps = landing.partition_gaps(con, contract(tmp_path), date(2026, 11, 2))["mensal"]
    assert gaps["indisponiveis"] == [202609] and 202610 in gaps["faltam"]


def ok_downloader(url: str, folder: Path) -> tuple[Path, str, int]:
    folder.mkdir(parents=True, exist_ok=True)
    file = folder / url.rsplit("/", 1)[-1]
    file.write_text("codigo\n1\n", encoding="utf-8")
    return file, f"h{url}", file.stat().st_size


def no_head(url: str) -> dict[str, str | None]:
    return {}


def test_a_blocked_source_records_the_block_and_stops_the_rest_of_the_plan(
    con: Connection, tmp_path: Path, settings: Settings
) -> None:
    asked: list[str] = []

    def second_is_blocked(url: str, folder: Path) -> tuple[Path, str, int]:
        asked.append(url)
        if url.endswith("2025.csv"):
            raise fetch.SourceBlocked(f"{url}: HTTP 429")
        return ok_downloader(url, folder)

    source = contract(tmp_path)
    items: list[landing.Item] = [("votos", 2024), ("votos", 2025), ("votos", 2026)]
    done = landing.extract_plan(con, settings, source, items, second_is_blocked, no_head)
    assert done == 1 and len(asked) == 2  # o terceiro nem é pedido
    assert monitoring.latest_status(con, "teste", "votos")[0] == "error"
    # a fonte volta a responder: o bloqueio deixa de contar
    assert landing.extract_plan(con, settings, source, items[1:2], ok_downloader, no_head) == 1
    assert not [d for d in monitoring.latest_status(con, "teste", "votos")[1] if "bloqueio" in d]


def test_a_head_that_the_source_refuses_does_not_block_the_download(
    con: Connection, tmp_path: Path, settings: Settings
) -> None:
    def head_403(url: str) -> dict[str, str | None]:
        raise fetch.SourceBlocked(f"{url}: HTTP 403")

    done = landing.extract_plan(con, settings, contract(tmp_path), [("votos", 2024)], ok_downloader, head_403)
    assert done == 1
    assert con.execute("SELECT count(*) FROM metadata.capturas").fetchone() == (1,)
    assert con.execute(
        "SELECT count(*) FROM metadata.fontes_verificacoes WHERE verificacao = 'bloqueio'"
    ).fetchone() == (0,)


def test_an_on_demand_dataset_is_out_of_the_incremental_plan_the_recovery_and_the_gap_alert(
    con: Connection, tmp_path: Path
) -> None:
    c = contract(tmp_path)
    assert not [i for i in landing.plan_incremental(c, TODAY) if i[0] == "fotos"]
    assert not [i for i in landing.plan_recovery(con, c, TODAY) if i[0] == "fotos"]
    assert landing.partition_gaps(con, c, TODAY)["fotos"]["faltam"] == []
    landing.record_gaps(con, c)
    row = con.execute(
        "SELECT resultado FROM metadata.fontes_verificacoes WHERE dataset = 'fotos' AND verificacao = 'particoes'"
    ).fetchone()
    assert row == ("ok",)
    assert (  # pedido explícito inclui
        "fotos",
        2024,
    ) in landing.plan(c, [2024])
