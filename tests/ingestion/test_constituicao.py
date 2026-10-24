"""Fonte da Constituição: acha o link atual na página, guarda o arquivo original com hash e lê um parágrafo por linha."""

from pathlib import Path

import pytest

from dado_publico_brasil.ingestion import contract as contracts
from dado_publico_brasil.ingestion import fetch
from dado_publico_brasil.ingestion.contract import InvalidContract, load_contract
from dado_publico_brasil.ingestion.custom.legislativo.federal import constituicao

PAGE = """<a href="/x/arquivos/ConstituicaoTextoAtualizado_EC%20139.html">139</a>
<a href="/x/arquivos/ConstituicaoTextoAtualizado_EC%20141.html">141</a>
<a href="/x/arquivos/.lixeira/ConstituicaoTextoAtualizado_EC%20150.html">lixeira</a>
<a href="/x/arquivos/ConstituicaoTextoAtualizado_EC%20141.pdf">pdf</a>
<a href="/x/arquivos/constituicao-adct-de-1988_ec-136.html">adct</a>"""
URL = "https://exemplo.leg.br/x/constituicao1988?parte="


@pytest.fixture
def page(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(fetch, "get", lambda url, headers=None: (200, PAGE.encode()))


def test_the_link_is_the_html_with_the_highest_amendment_and_never_the_trash_or_other_formats(
    page: None,
) -> None:
    link, part, amendment = constituicao._resolve(URL + "constituicao")
    assert (link, part, amendment) == (
        "https://exemplo.leg.br/x/arquivos/ConstituicaoTextoAtualizado_EC%20141.html",
        "constituicao",
        141,
    )
    assert constituicao._resolve(URL + "adct")[2] == 136


def test_a_page_without_the_file_or_with_an_error_fails_loudly(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(fetch, "get", lambda url, headers=None: (200, b"<p>sem links</p>"))
    with pytest.raises(RuntimeError, match="nenhum arquivo HTML"):
        constituicao._resolve(URL + "constituicao")
    monkeypatch.setattr(fetch, "get", lambda url, headers=None: (503, b""))
    with pytest.raises(RuntimeError, match="respondeu 503"):
        constituicao._resolve(URL + "constituicao")


def test_the_original_file_is_kept_unchanged_with_the_amendment_and_the_hash_in_the_name(
    page: None, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def fake_download(
        url: str, folder: Path, headers: None = None, suffix: str = "csv"
    ) -> tuple[Path, str, int]:
        folder.mkdir(parents=True, exist_ok=True)
        temporary = folder / "baixado.html"
        temporary.write_bytes(b"<p>texto</p>")
        return temporary, "abcdef0123456789" * 4, 12

    monkeypatch.setattr(fetch, "download", fake_download)
    file, digest, size = constituicao.download(URL + "constituicao", tmp_path)
    assert file.name == "constituicao-ec141-abcdef012345.html" and file.read_bytes() == b"<p>texto</p>"
    assert (digest[:6], size) == ("abcdef", 12)
    assert not (tmp_path / "baixado.html").exists()


def test_records_are_the_non_empty_paragraphs_in_order_with_the_amendment_of_the_file(tmp_path: Path) -> None:
    file = tmp_path / "constituicao-ec141-abc.html"
    file.write_text(
        "<p>Primeiro &amp; <b>negrito</b></p><p> </p><p>Art. 1&ordm; Segundo\n  em duas linhas</p>",
        encoding="utf-8",
    )
    found = list(constituicao.records(file, contracts.find("constituicao").datasets["constituicao"]))
    assert found == [
        {"ordem": 1, "linha": "Primeiro & negrito", "emenda_do_arquivo": "141"},
        {"ordem": 2, "linha": "Art. 1º Segundo em duas linhas", "emenda_do_arquivo": "141"},
    ]


def test_an_html_contract_needs_its_own_reader_because_there_is_no_default(tmp_path: Path) -> None:
    file = tmp_path / "semleitor.yml"
    file.write_text(
        "source: semleitor\npower: legislativo\nlevel: federal\naccess: {base_url: http://x, format: html}\n"
        "datasets:\n  d: {url: '{base_url}/d', load: full, write: replace, columns: [a]}\n",
        encoding="utf-8",
    )
    with pytest.raises(InvalidContract, match="html"):
        load_contract(file)
