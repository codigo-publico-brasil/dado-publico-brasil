"""`missing_status` (ADR 0059): host que responde 403 para arquivo inexistente, com servidor local (sem rede externa)."""

import threading
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from dado_publico_brasil.core import runs
from dado_publico_brasil.core.settings import Settings
from dado_publico_brasil.core.warehouse import Connection
from dado_publico_brasil.ingestion import landing
from dado_publico_brasil.ingestion.contract import InvalidContract, SourceContract, load_contract

TODAY = date(2026, 7, 10)  # lag_months: 1 -> o mês mais recente do plano é 202606
HEADER = """
source: teste
power: executivo
level: federal
description: Fonte de teste
schedule: "0 6 * * *"
access: {base_url: "BASE", delimiter: ",", encoding: utf-8, rate_limit: 1000}
datasets:
"""
MONTH = """  mensal:
    url: "{base_url}/{month}_Dados.csv"
    load: yearly
    partition: month
    first_month: 202601
    lag_months: 1
    write: replace
    columns: [c]
"""
PRESENT = {"202601", "202602", "202604"}  # os 3 de 6 que existem; 202603 (meio), 202605 e 202606 dão o código


def contract(tmp_path: Path, base: str, extra: str = "    missing_status: [403]\n") -> SourceContract:
    file = tmp_path / "contract.yml"
    file.write_text(HEADER.replace("BASE", base) + MONTH + extra, encoding="utf-8")
    return load_contract(file)


@contextmanager
def server(code: int = 403) -> Iterator[tuple[str, list[str]]]:
    gets: list[str] = []

    class Handler(BaseHTTPRequestHandler):
        def answer(self) -> bool:
            if self.path[1:7] not in PRESENT:
                self.send_error(code)
                return False
            self.send_response(200)
            self.send_header("Content-Type", "text/csv")
            self.send_header("Content-Length", "4")
            self.end_headers()
            return True

        def do_GET(self) -> None:
            gets.append(self.path[1:7])
            if self.answer():
                self.wfile.write(b"c\n1\n")

        def do_HEAD(self) -> None:
            self.answer()

        def log_message(self, *args: object) -> None:
            pass

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    try:
        yield f"http://127.0.0.1:{httpd.server_port}", gets
    finally:
        httpd.shutdown()
        httpd.server_close()


def captured(con: Connection) -> list[int]:
    return [r[0] for r in con.execute("SELECT particao FROM metadata.capturas ORDER BY particao").fetchall()]


def checks(con: Connection, kind: str) -> list[tuple[int, str]]:
    return con.execute(
        "SELECT particao, coalesce(tipo_ocorrencia, '') FROM metadata.fontes_verificacoes "
        "WHERE verificacao = ? AND resultado = 'error' ORDER BY particao",
        (kind,),
    ).fetchall()


@pytest.fixture(autouse=True)
def today(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(runs, "today", lambda: TODAY)


def test_with_the_key_the_missing_months_are_not_published_and_the_source_is_not_stopped(
    con: Connection, settings: Settings, tmp_path: Path
) -> None:
    with server() as (base, _):
        source = contract(tmp_path, base)
        items = landing.plan(source, [2026])
        assert landing.extract_plan(con, settings, source, items) == 6  # nenhum item interrompeu o plano
    assert captured(con) == [202601, 202602, 202604]
    assert checks(con, "bloqueio") == []
    assert checks(con, "availability") == [
        (202603, "nao_publicado"),
        (202605, "nao_publicado"),
        (202606, "nao_publicado"),
    ]
    gap = landing.partition_gaps(con, source, TODAY)["mensal"]
    assert gap["capturadas"] == 3 and gap["faltam"] == [202603, 202605, 202606] and gap["indisponiveis"] == []
    particoes = con.execute(
        "SELECT resultado FROM metadata.fontes_verificacoes WHERE verificacao = 'particoes'"
    ).fetchall()
    assert particoes == [("warn",)]  # a lacuna continua contada, sem virar erro de bloqueio


def test_without_the_key_the_old_behaviour_stays_a_block(
    con: Connection, settings: Settings, tmp_path: Path
) -> None:
    with server() as (base, _):
        source = contract(tmp_path, base, extra="")
        items = landing.plan(source, [2026])
        assert landing.extract_plan(con, settings, source, items) == 2  # para no 403 de 202603
    assert captured(con) == [202601, 202602]
    assert checks(con, "bloqueio") == [(202603, "bloqueio")]


@pytest.mark.parametrize("code", [405, 429])
def test_405_and_429_stay_a_block_even_with_the_key(
    con: Connection, settings: Settings, tmp_path: Path, code: int
) -> None:
    with server(code) as (base, _):
        source = contract(tmp_path, base)
        assert landing.extract_plan(con, settings, source, landing.plan(source, [2026])) == 2
    assert checks(con, "bloqueio") == [(202603, "bloqueio")]
    assert checks(con, "availability") == []


def test_a_second_run_does_not_recapture_and_each_missing_month_is_asked_once_per_run(
    con: Connection, settings: Settings, tmp_path: Path
) -> None:
    with server() as (base, gets):
        source = contract(tmp_path, base)
        items = landing.plan(source, [2026])
        landing.extract_plan(con, settings, source, items, recover=True)
        first = con.execute("SELECT count(*), sum(hash(sha256)) FROM metadata.capturas").fetchone()
        assert gets.count("202603") == 1  # o recover não repete o mês que o plano já pediu
        gets.clear()
        landing.extract_plan(con, settings, source, items, recover=True)
        assert con.execute("SELECT count(*), sum(hash(sha256)) FROM metadata.capturas").fetchone() == first
        assert gets.count("202603") == 1 and gets.count("202601") == 1  # um GET por mês, sem duplicar


def test_months_already_seen_as_not_published_go_last_in_the_recovery(
    con: Connection, settings: Settings, tmp_path: Path
) -> None:
    with server() as (base, _):
        source = contract(tmp_path, base)
        landing.extract_plan(con, settings, source, [("mensal", 202605), ("mensal", 202603)])
        order = [p for _, p in landing.plan_recovery(con, source, TODAY, limit=9)]
    assert order == [202604, 202602, 202601, 202605, 202603]  # o que nunca foi pedido vem antes
    assert [p for _, p in landing.plan_recovery(con, source, TODAY, limit=3)] == [202604, 202602, 202601]


def test_the_key_does_not_change_the_plan(tmp_path: Path) -> None:
    with_key, without = contract(tmp_path, "http://x"), contract(tmp_path, "http://x", extra="")
    for plan in (landing.plan(with_key, [2026]), landing.plan_incremental(with_key, TODAY)):
        assert plan
    assert landing.plan(with_key, [2026]) == landing.plan(without, [2026])
    assert landing.plan_incremental(with_key, TODAY) == landing.plan_incremental(without, TODAY)


@pytest.mark.parametrize("bad", ["[405]", "[429]", "[200]", '["403"]', "403"])
def test_an_invalid_missing_status_is_refused(tmp_path: Path, bad: str) -> None:
    with pytest.raises(InvalidContract, match="missing_status"):
        contract(tmp_path, "http://x", extra=f"    missing_status: {bad}\n")
