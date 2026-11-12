"""Partição diária (`partition: day`, ADR 0058): janela, atraso, dia futuro, 404 e idempotência, sem rede externa."""

import hashlib
import threading
import zipfile
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from dado_publico_brasil.core import runs
from dado_publico_brasil.core.settings import Settings
from dado_publico_brasil.core.warehouse import Connection
from dado_publico_brasil.ingestion import arquivos, landing
from dado_publico_brasil.ingestion.contract import InvalidContract, SourceContract, load_contract

TODAY = date(2026, 10, 24)
HEADER = """
source: teste
power: executivo
level: federal
description: Fonte de teste
schedule: "0 6 * * *"
access: {base_url: "BASE", delimiter: ",", encoding: utf-8, rate_limit: 1000}
datasets:
"""
DAY = """  dia:
    url: "{base_url}/{day}_Despesas.zip"
    load: yearly
    partition: day
    first_day: 20261020
    lag_days: 1
    archive: zip
    write: replace
    columns: [codigo]
    files: {collection: arq, member: '^(?P<x>.+)\\.csv$', path: "{partition}/{x}.csv"}
"""
CSV_DAY = DAY.split("    archive:")[0] + "    columns: [codigo]\n    write: replace\n"
OTHERS = """  anual: {url: "{base_url}/a-{year}.csv", load: yearly, first_year: 2020, write: replace, columns: [c]}
  mensal: {url: "{base_url}/m-{month}.zip", load: yearly, partition: month, first_month: 202601, lag_months: 1, archive: zip, raw: false}
  sequencia: {url: "{base_url}/s-{partition}.csv", load: yearly, partition: sequence, sequence: {first_year: 2019, first_value: 56, years: 4}, write: replace, columns: [c]}
"""


def contract(tmp_path: Path, body: str = DAY, base: str = "http://exemplo") -> SourceContract:
    file = tmp_path / "contract.yml"
    file.write_text(HEADER.replace("BASE", base) + body, encoding="utf-8")
    return load_contract(file)


def test_the_plan_has_the_days_from_first_day_up_to_the_lag_and_never_a_future_day(tmp_path: Path) -> None:
    d = contract(tmp_path).datasets["dia"]
    assert landing.partitions(d, {2026}, TODAY) == [20261020, 20261021, 20261022, 20261023]
    assert landing.partitions(d, {2025}, TODAY) == []
    assert landing.current_partition(d, TODAY) == 20261023  # lag_days: 1
    assert landing.current_partition(d, date(2027, 1, 1)) == 20261231  # a virada do ano
    assert landing.partitions(d, {2026, 2027}, date(2027, 1, 2))[-2:] == [20261231, 20270101]
    zero = contract(tmp_path, DAY.replace("    lag_days: 1\n", "")).datasets["dia"]
    assert landing.partitions(zero, {2026}, TODAY)[-1] == 20261024  # sem atraso, hoje já é pedido
    assert landing.partitions(zero, {2026}, date(2026, 10, 19)) == []  # antes de first_day, nada


def test_the_incremental_plan_is_the_latest_day_and_on_demand_stays_out(tmp_path: Path) -> None:
    old = DAY.replace("  dia:", "  historico:").replace("20261020", "20260101")
    source = contract(tmp_path, DAY + old.replace("lag_days: 1", "lag_days: 1\n    on_demand: true"))
    assert landing.plan_incremental(source, TODAY) == [("dia", 20261023)]
    assert ("historico", 20260101) in landing.plan(source, [2026])  # pedido explícito vale
    assert landing.plan(source, [2026]).count(("dia", 20261020)) == 1


def test_the_url_and_the_files_path_take_the_day(tmp_path: Path, settings: Settings, con: Connection) -> None:
    source = contract(tmp_path)
    assert source.url("dia", 20261023) == "http://exemplo/20261023_Despesas.zip"
    file = settings.landing_dir / "teste" / "dia" / "x.zip"
    file.parent.mkdir(parents=True)
    with zipfile.ZipFile(file, "w") as package:
        package.writestr("a.csv", "codigo\n1\n")
    landing.register_capture(
        con, "teste", "dia", 20261023, source.url("dia", 20261023), "h", 1,
        file.relative_to(settings.storage_root).as_posix(), 0,
    )  # fmt: skip
    assert arquivos.materialize(con, settings, source) == 1
    base = settings.storage_root / "arquivos"
    assert [p.relative_to(base).as_posix() for p in base.rglob("*.csv")] == [
        "executivo/federal/teste/arq_arq/20261023/a.csv"
    ]


@pytest.mark.parametrize(
    "change",
    [
        ("    first_day: 20261020\n", ""),  # partition: day sem first_day
        ("partition: day", "partition: month"),  # first_day sem partition: day
        ("first_day: 20261020", "first_day: 20261320"),  # data que não existe
        ("lag_days: 1", "lag_days: -1"),
    ],
)
def test_an_inconsistent_day_declaration_is_refused(tmp_path: Path, change: tuple[str, str]) -> None:
    with pytest.raises(InvalidContract):
        contract(tmp_path, DAY.replace(*change))


def test_lag_days_outside_a_daily_partition_is_refused(tmp_path: Path) -> None:
    anual = OTHERS.splitlines()[0].replace("}", ", lag_days: 1}") + "\n"
    with pytest.raises(InvalidContract, match="lag_days"):
        contract(tmp_path, anual)


def test_year_month_and_sequence_plans_are_the_same_as_before(tmp_path: Path) -> None:
    """Prova de não regressão: contagem e hash dos planos medidos em `main`, antes da partição diária."""
    source = contract(tmp_path, OTHERS)

    def sign(items: list[landing.Item]) -> tuple[int, str]:
        return len(items), hashlib.sha256(repr(items).encode()).hexdigest()[:16]

    assert sign(landing.plan(source, [2024, 2025, 2026])) == (14, "1f73145f21a7cf6f")
    assert sign(landing.plan_incremental(source, TODAY)) == (4, "0b8df9f05ad9f800")
    assert sign(landing.plan_historical(source, 2020, 2026)) == (19, "7e46d29c753aa44f")


@contextmanager
def server(missing: set[str]) -> Iterator[str]:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            if any(m in self.path for m in missing):
                self.send_error(404)
                return
            body = b"PK"
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_HEAD(self) -> None:
            self.send_error(405)

        def log_message(self, *args: object) -> None:
            pass

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    try:
        yield f"http://127.0.0.1:{httpd.server_port}"
    finally:
        httpd.shutdown()
        httpd.server_close()


def test_a_404_day_is_not_published_and_the_rerun_does_not_duplicate_captures(
    con: Connection, settings: Settings, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(runs, "today", lambda: TODAY)
    with server({"20261021", "20261023"}) as base:
        source = contract(tmp_path, CSV_DAY, base)
        items = landing.plan(source, [2026])
        landing.extract_plan(con, settings, source, items)
        first = con.execute("SELECT count(*) FROM metadata.capturas").fetchone()
        landing.extract_plan(con, settings, source, items)
        assert con.execute("SELECT count(*) FROM metadata.capturas").fetchone() == first == (2,)
        kinds = dict(
            con.execute(
                "SELECT particao, tipo_ocorrencia FROM metadata.fontes_verificacoes "
                "WHERE verificacao = 'availability' AND resultado = 'error'"
            ).fetchall()
        )
        assert kinds == {
            20261021: "nao_encontrado",
            20261023: "nao_publicado",
        }  # o último dia ainda pode sair
        gaps = landing.partition_gaps(con, source, TODAY)["dia"]
        assert gaps["indisponiveis"] == [20261021] and gaps["faltam"] == [20261023]  # o último segue pedido
        assert landing.plan_recovery(con, source, TODAY) == []  # o dia em curso é do plano incremental


def test_recovery_asks_every_missing_day_of_the_window_and_skips_on_demand(
    con: Connection, tmp_path: Path
) -> None:
    source = contract(tmp_path, DAY.replace("20261020", "20260901"))
    landing.register_capture(con, "teste", "dia", 20260901, source.url("dia", 20260901), "h", 1, "x", 0)
    missing = landing.plan_recovery(con, source, TODAY)
    assert len(missing) == 51  # 1/set a 23/out são 53 dias, menos o capturado e o dia em curso
    assert missing[0] == ("dia", 20261022) and ("dia", 20260901) not in missing
    ondemand = contract(tmp_path, DAY.replace("lag_days: 1", "lag_days: 1\n    on_demand: true"))
    assert landing.plan_recovery(con, ondemand, TODAY) == []
