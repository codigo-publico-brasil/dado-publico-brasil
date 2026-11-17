"""Cache negativo e uma pergunta por arquivo (ADR 0061), com servidor local que conta as requisições."""

import hashlib
import threading
from collections import Counter
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, date, datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from dado_publico_brasil.core import runs
from dado_publico_brasil.core.settings import Settings
from dado_publico_brasil.core.warehouse import Connection
from dado_publico_brasil.ingestion import landing
from dado_publico_brasil.ingestion.contract import SourceContract, load_contract

START = datetime(2026, 7, 10, 3, 0, tzinfo=UTC)  # lag_months: 1 -> o mês em curso do plano é 202606
TODAY = date(2026, 7, 10)
HEADER = """
source: teste
power: executivo
level: federal
description: Fonte de teste
schedule: "0 6 * * *"
access: {base_url: "BASE", delimiter: ",", encoding: utf-8, rate_limit: 1000}
datasets:
"""
DATASET = """  {name}:
    url: "{{base_url}}/{{month}}_Dados.csv#{name}"
    load: yearly
    partition: month
    first_month: 202507
    lag_months: 1
    write: replace
    columns: [c]
    missing_status: [403]
"""
MONTHS = [f"2025{m:02d}" for m in range(7, 13)] + [f"2026{m:02d}" for m in range(1, 7)]  # 202507..202606
Log = list[tuple[str, str]]  # (método, mês)


def body(month: str) -> bytes:
    return f"c\n{month}\n".encode()


@contextmanager
def server(present: set[str], code: int = 403) -> Iterator[tuple[str, Log]]:
    log: Log = []

    class Handler(BaseHTTPRequestHandler):
        def serve(self, send_body: bool) -> None:
            month = self.path[1:7]
            log.append((self.command, month))
            if month not in present:
                self.send_error(code)
                return
            self.send_response(200)
            self.send_header("Content-Type", "text/csv")
            self.send_header("Content-Length", str(len(body(month))))
            self.send_header("Last-Modified", "Mon, 01 Jun 2026 00:00:00 GMT")
            self.end_headers()
            if send_body:
                self.wfile.write(body(month))

        def do_GET(self) -> None:
            self.serve(True)

        def do_HEAD(self) -> None:
            self.serve(False)

        def log_message(self, *args: object) -> None:
            pass

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    try:
        yield f"http://127.0.0.1:{httpd.server_port}", log
    finally:
        httpd.shutdown()
        httpd.server_close()


def contract(tmp_path: Path, base: str, names: str = "abcd") -> SourceContract:
    file = tmp_path / "contract.yml"
    file.write_text(
        HEADER.replace("BASE", base) + "".join(DATASET.format(name=n) for n in names), encoding="utf-8"
    )
    return load_contract(file)


class Night:
    """Roda a execução incremental (plano normal e recuperação) `days` dias depois do início."""

    def __init__(
        self, con: Connection, settings: Settings, source: SourceContract, mp: pytest.MonkeyPatch, log: Log
    ):
        self.con, self.settings, self.source, self.mp, self.log = con, settings, source, mp, log

    def run(self, days: int) -> Counter[tuple[str, str]]:
        moment = START + timedelta(days=days)
        self.mp.setattr(runs, "now", lambda: moment.isoformat(timespec="seconds"))
        self.mp.setattr(runs, "today", lambda: TODAY)  # o mês em curso do plano não muda no teste
        self.log.clear()
        items = landing.plan_incremental(self.source, TODAY)
        landing.extract_plan(self.con, self.settings, self.source, items, recover=True)
        return Counter(self.log)


@pytest.fixture
def night(
    con: Connection, settings: Settings, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Iterator[tuple[Night, set[str]]]:
    present = set(MONTHS[:4])  # 202507..202510 existem; 202511..202606 dão 403
    with server(present) as (base, log):
        yield Night(con, settings, contract(tmp_path, base), monkeypatch, log), present


def test_one_request_per_file_not_per_dataset_and_the_negative_cache_holds_for_the_period(
    night: tuple[Night, set[str]],
) -> None:
    run, _ = night
    first = run.run(0)
    # 4 arquivos (mês em curso, o anterior e 2 outros da recuperação, que tem 3 vagas e o anterior é um), um HEAD e um GET cada, para 4 datasets irmãos
    files = {"202606", "202605", "202604", "202603"}
    assert set(first) == {(method, month) for method in ("HEAD", "GET") for month in files}
    assert set(first.values()) == {1}
    for day in (1, 6):  # dentro do prazo, os vistos como não publicados não são sondados de novo
        probed = {month for _, month in run.run(day)}
        assert probed.isdisjoint({"202604", "202603"})
        assert {"202606", "202605"} <= probed  # o mês em curso e o anterior, toda noite


def test_after_the_period_it_is_probed_again_and_a_month_that_appears_is_captured_once(
    night: tuple[Night, set[str]],
) -> None:
    run, present = night
    for day in range(7):  # o backlog anda: cada noite pede 3 meses que ainda não foram vistos
        run.run(day)
    present.add("202604")  # o portal publica o mês
    probed = run.run(7)  # os 2 meses vistos na noite 0 vencem agora; os das noites 1 e 2 ainda não
    assert {"202604", "202603"} <= {month for _, month in probed}
    assert not {"202602", "202601", "202512", "202511"} & {month for _, month in probed}
    assert probed[("GET", "202604")] == 1  # um GET para os 4 irmãos
    captured = run.con.execute("SELECT dataset FROM metadata.capturas WHERE particao = 202604").fetchall()
    assert sorted(captured) == [("a",), ("b",), ("c",), ("d",)]
    assert 202604 not in [p for _, p in landing.plan_recovery(run.con, run.source, TODAY)]


def test_each_dataset_still_records_its_own_check(night: tuple[Night, set[str]]) -> None:
    run, _ = night
    run.run(0)
    rows = run.con.execute(
        "SELECT dataset, count(*) FROM metadata.fontes_verificacoes WHERE verificacao = 'availability' "
        "AND tipo_ocorrencia = 'nao_publicado' AND particao = 202604 GROUP BY dataset ORDER BY dataset"
    ).fetchall()
    assert rows == [("a", 1), ("b", 1), ("c", 1), ("d", 1)]


def test_an_explicit_request_ignores_the_negative_cache(night: tuple[Night, set[str]]) -> None:
    run, _ = night
    run.run(0)
    run.log.clear()
    landing.extract_plan(run.con, run.settings, run.source, [("a", 202604)])  # `--months`
    assert ("GET", "202604") in run.log


def test_the_captures_are_the_ones_of_the_months_that_exist(night: tuple[Night, set[str]]) -> None:
    run, present = night
    for day in range(4):
        run.run(day)
    count, shas = run.con.execute(
        "SELECT count(*), list(DISTINCT sha256) FROM metadata.capturas"
    ).fetchone() or (0, [])
    assert count == 4 * len(present)
    assert set(shas) == {hashlib.sha256(body(m)).hexdigest() for m in present}
    assert all(n == 1 for (method, _), n in Counter(run.log).items() if method == "GET")


@pytest.mark.parametrize("code", [405, 429])
def test_405_and_429_stay_a_block(
    con: Connection, settings: Settings, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, code: int
) -> None:
    with server(set(), code) as (base, log):
        Night(con, settings, contract(tmp_path, base), monkeypatch, log).run(0)
    blocks = con.execute(
        "SELECT count(*) FROM metadata.fontes_verificacoes WHERE verificacao = 'bloqueio'"
    ).fetchone()
    assert blocks == (1,)
