"""Lacunas de partição e recuperação depois de uma pausa (issues 53 e 54)."""

from datetime import date
from pathlib import Path

from dado_publico_brasil.core import runs
from dado_publico_brasil.core.settings import Settings
from dado_publico_brasil.core.warehouse import Connection
from dado_publico_brasil.ingestion import landing, monitoring
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
    monitoring.record(con, "teste", "votos", 2022, "availability", "error", "HTTP Error 404: Not Found")
    monitoring.record(con, "teste", "votos", 2023, "availability", "error", "timed out")  # transitório
    gaps = landing.partition_gaps(con, contract(tmp_path), TODAY)["votos"]
    assert gaps["indisponiveis"] == [2022]
    assert 2022 not in gaps["faltam"] and 2023 in gaps["faltam"]
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
        "SELECT status, detail FROM metadata.source_checks WHERE check_name = 'particoes' AND dataset = 'votos'"
    ).fetchone()
    assert row is not None and row[0] == "warn" and "1 de" in row[1] and "faltam:" in row[1]
