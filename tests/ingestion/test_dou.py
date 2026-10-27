"""Fonte do DOU: um zip por seção e mês, só no landing (sem tabela no raw)."""

import hashlib
import io
import zipfile
from datetime import date
from pathlib import Path

import pytest

from dado_publico_brasil.core.settings import Settings
from dado_publico_brasil.core.warehouse import Connection, rows, scalar
from dado_publico_brasil.ingestion import contract as contracts
from dado_publico_brasil.ingestion import fetch, landing, loader
from dado_publico_brasil.ingestion.custom.executivo.federal import dou

LINK = "https://www.in.gov.br/documents/49035712/740172584/S01102026_Atualizado185748.zip/668c-0b48?version=1.0&amp;t=1&amp;download=true"
PAGE = f"""<a href="{LINK}">S01</a>
<a href="https://www.in.gov.br/documents/49035712/740172584/S02102026_Atualizado190011.zip/e33c-4e42?version=1.0&amp;t=2&amp;download=true">S02</a>
<a href="https://www.in.gov.br/documents/1/2/S01092026.zip/aaaa?version=1.0&amp;t=3&amp;download=true">S01 de setembro</a>"""
URL = "https://www.in.gov.br/acesso-a-informacao/dados-abertos/base-de-dados?ano={}&secao={}"


def test_the_plan_is_one_zip_per_section_and_month_from_the_first_month_and_the_daily_plan_has_only_the_current_month() -> (
    None
):
    source = contracts.find("dou")
    plan = landing.plan(source, [2026])
    assert {name for name, _ in plan} == {"secao1", "secao2", "secao3"}
    months = sorted({value for _, value in plan if value is not None})
    assert months[0] == 202608 and months == list(
        range(202608, months[-1] + 1)
    )  # mês corrente incluso, sem pular
    daily = landing.plan_incremental(source, today=date(2026, 10, 24))
    assert {part for _, part in daily} == {
        202610
    }  # o diário confere só o mês em curso; os anteriores, sob pedido


def test_the_link_is_the_zip_of_the_requested_section_and_month(monkeypatch: pytest.MonkeyPatch) -> None:
    pages: list[tuple[str, dict[str, str] | None]] = []

    def get(url: str, headers: dict[str, str] | None = None) -> tuple[int, bytes]:
        pages.append((url, headers))
        return 200, PAGE.encode()

    monkeypatch.setattr(fetch, "get", get)
    link, name = dou._resolve(URL.format(202610, 1))
    assert name == "S01102026_Atualizado185748.zip"
    assert link == LINK.replace("&amp;", "&")
    assert dou._resolve(URL.format(202609, 1))[1] == "S01092026.zip"
    assert pages[0] == (
        "https://www.in.gov.br/acesso-a-informacao/dados-abertos/base-de-dados?ano=2026&mes=Outubro",
        {"Accept": "*/*"},
    )


def test_a_missing_section_or_a_page_error_fails_loudly(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(fetch, "get", lambda url, headers=None: (200, PAGE.encode()))
    with pytest.raises(OSError, match="nenhum zip da seção 3"):
        dou._resolve(URL.format(202610, 3))
    monkeypatch.setattr(fetch, "get", lambda url, headers=None: (403, b""))
    with pytest.raises(OSError, match="403"):
        dou._resolve(URL.format(202610, 1))


def test_a_landing_only_dataset_is_kept_with_hash_and_never_loaded_into_the_raw(
    con: Connection, settings: Settings, tmp_path: Path
) -> None:
    source = contracts.find("dou")
    buffer = io.BytesIO()  # um zip de verdade: a conferência de integridade abre o pacote e exige um XML
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("ato.xml", "<xml/>")
    content = buffer.getvalue()

    def downloader(url: str, folder: Path) -> tuple[Path, str, int]:
        folder.mkdir(parents=True, exist_ok=True)
        file = folder / "S01102026_Atualizado185748-abc.zip"
        file.write_bytes(content)
        return file, hashlib.sha256(content).hexdigest(), len(content)

    capture = landing.extract(
        con, settings, source, "secao1", 202610, downloader=downloader, head_request=lambda url: {}
    )
    assert capture > 0
    assert rows(con, "SELECT dataset, year FROM metadata.captures") == [{"dataset": "secao1", "year": 202610}]
    assert scalar(con, "SELECT count(*) FROM metadata.source_checks WHERE check_name = 'schema'") == 0
    assert loader.load_pending(con, settings, source) == (0, 0)
    assert scalar(con, "SELECT loaded_at IS NULL FROM metadata.captures")
