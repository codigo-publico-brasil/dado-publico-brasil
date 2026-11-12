"""Caminhos da captura de uma URL (`landing.extract`): baixar, reaproveitar, pular, falhar, bloquear."""

from datetime import date
from http.client import HTTPException
from pathlib import Path

import pytest

from dado_publico_brasil.core import runs
from dado_publico_brasil.core.settings import Settings
from dado_publico_brasil.core.warehouse import Connection, scalar
from dado_publico_brasil.ingestion import fetch, landing
from dado_publico_brasil.ingestion.contract import SourceContract, load_contract
from dado_publico_brasil.ingestion.fetch import Downloader

CONTRACT = """
source: teste
power: legislativo
level: federal
description: Fonte de teste
access: {base_url: "http://exemplo", delimiter: ",", encoding: utf-8}
datasets:
  a:
    url: "{base_url}/pacote.csv#a"
    load: full
    write: replace
    columns: [codigo]
  b:
    url: "{base_url}/pacote.csv#b"
    load: full
    write: replace
    columns: [codigo]
  mensal:
    url: "{base_url}/mes-{year}.zip"
    load: yearly
    partition: month
    first_month: 202608
    archive: zip
    raw: false
"""
ETAG = {"etag": '"v1"', "last_modified": None, "size": None}


@pytest.fixture
def source(tmp_path: Path) -> SourceContract:
    file = tmp_path / "contract.yml"
    file.write_text(CONTRACT, encoding="utf-8")
    return load_contract(file)


class Server:
    """Baixa um conteúdo e conta os pedidos."""

    def __init__(self, content: bytes = b"codigo\n1\n") -> None:
        self.content, self.calls = content, 0

    def __call__(self, url: str, folder: Path) -> tuple[Path, str, int]:
        import hashlib

        self.calls += 1
        folder.mkdir(parents=True, exist_ok=True)
        file = folder / "pacote.csv"
        file.write_bytes(self.content)
        return file, hashlib.sha256(self.content).hexdigest(), len(self.content)


def head(url: str) -> dict[str, str | None]:
    return dict(ETAG)


def failing(error: Exception) -> Downloader:
    def download(url: str, folder: Path) -> tuple[Path, str, int]:
        raise error

    return download


def test_a_lost_local_file_comes_back_to_the_registered_path_when_the_content_is_the_same(
    con: Connection, settings: Settings, source: SourceContract
) -> None:
    server = Server()
    first = landing.extract(con, settings, source, "a", downloader=server, head_request=lambda u: {})
    path = settings.storage_root / scalar(
        con, "SELECT caminho FROM metadata.capturas WHERE id_captura = ?", (first,)
    )
    path.unlink()
    again = landing.extract(con, settings, source, "a", downloader=server, head_request=lambda u: {})
    assert again == first and server.calls == 2 and path.exists()
    assert scalar(con, "SELECT count(*) FROM metadata.capturas") == 1
    assert [p for p in settings.landing_dir.rglob("*") if p.is_file()] == [path]


def test_the_same_content_on_another_day_keeps_the_old_file_and_removes_the_new_one(
    con: Connection, settings: Settings, source: SourceContract, monkeypatch: pytest.MonkeyPatch
) -> None:
    server = Server()
    monkeypatch.setattr(runs, "now", lambda: "2026-10-01T10:00:00+00:00")
    first = landing.extract(con, settings, source, "a", downloader=server, head_request=lambda u: {})
    monkeypatch.setattr(runs, "now", lambda: "2026-10-02T10:00:00+00:00")
    assert landing.extract(con, settings, source, "a", downloader=server, head_request=lambda u: {}) == first
    assert len([p for p in settings.landing_dir.rglob("*") if p.is_file()]) == 1
    assert not list(settings.landing_dir.glob("teste/a/completo/20261002"))


def test_a_package_that_came_for_another_dataset_is_reused_without_a_new_download(
    con: Connection, settings: Settings, source: SourceContract
) -> None:
    server = Server()
    a = landing.extract(con, settings, source, "a", downloader=server, head_request=head)
    b = landing.extract(con, settings, source, "b", downloader=server, head_request=head)
    assert server.calls == 1 and a != b
    paths = con.execute("SELECT caminho, sha256 FROM metadata.capturas ORDER BY id_captura").fetchall()
    assert len(paths) == 2 and paths[0] == paths[1]


def test_force_downloads_even_if_the_source_says_nothing_changed(
    con: Connection, settings: Settings, source: SourceContract
) -> None:
    server = Server()
    first = landing.extract(con, settings, source, "a", downloader=server, head_request=head)
    forced = landing.extract(con, settings, source, "a", downloader=server, head_request=head, force=True)
    assert server.calls == 2 and forced == first  # o conteúdo é o mesmo: a captura é a mesma


@pytest.mark.parametrize("error", [OSError("fora do ar"), HTTPException("resposta ruim")])
def test_a_failed_download_records_the_error_and_returns_minus_one(
    con: Connection, settings: Settings, source: SourceContract, error: Exception
) -> None:
    assert landing.extract(con, settings, source, "a", downloader=failing(error), head_request=head) == -1
    assert scalar(con, "SELECT count(*) FROM metadata.capturas") == 0
    assert (
        scalar(con, "SELECT resultado FROM metadata.fontes_verificacoes WHERE verificacao = 'availability'")
        == "error"
    )


def test_a_403_on_the_current_month_is_not_yet_published_and_on_a_past_month_is_a_block(
    con: Connection, settings: Settings, source: SourceContract, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(runs, "today", lambda: date(2026, 10, 24))
    blocked = failing(fetch.SourceBlocked("x: HTTP 403", status=403))
    assert landing.extract(con, settings, source, "mensal", 202610, blocked, head) == -1
    assert con.execute(
        "SELECT tipo_ocorrencia, cd_status_http FROM metadata.fontes_verificacoes WHERE verificacao = 'availability'"
    ).fetchall() == [("nao_publicado", 403)]
    with pytest.raises(fetch.SourceBlocked):
        landing.extract(con, settings, source, "mensal", 202608, blocked, head)
