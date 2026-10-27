"""Integridade do download: o arquivo é o que se esperava antes de virar captura (issue 55)."""

import hashlib
import io
import zipfile
from collections.abc import Callable
from pathlib import Path

from dado_publico_brasil.core.settings import Settings
from dado_publico_brasil.core.warehouse import Connection, scalar
from dado_publico_brasil.ingestion import contract as contracts
from dado_publico_brasil.ingestion import landing

Download = Callable[[str, Path], tuple[Path, str, int]]


def serving(content: bytes) -> Download:
    """Um download que entrega estes bytes, com o hash no nome como o real."""

    def download(url: str, folder: Path) -> tuple[Path, str, int]:
        digest = hashlib.sha256(content).hexdigest()
        folder.mkdir(parents=True, exist_ok=True)
        file = folder / f"S01082026-{digest[:12]}.zip"
        file.write_bytes(content)
        return file, digest, len(content)

    return download


def zip_with(*names: str) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name in names:
            archive.writestr(name, b"<xml/>" if name.endswith(".xml") else b"x")
    return buffer.getvalue()


Check = tuple[str, str]


def extract(
    con: Connection, settings: Settings, content: bytes, size: str | None = None
) -> tuple[int, list[Check]]:
    def head(url: str) -> dict[str, str | None]:
        return {"etag": None, "last_modified": None, "size": size}

    found = landing.extract(con, settings, contracts.find("dou"), "secao1", 202608, serving(content), head)
    checks = con.execute(
        "SELECT status, detail FROM metadata.source_checks WHERE check_name = 'integridade' ORDER BY id"
    ).fetchall()
    return found, [(str(status), str(detail)) for status, detail in checks]


def test_a_good_zip_with_xml_becomes_a_capture(con: Connection, settings: Settings) -> None:
    found, checks = extract(con, settings, zip_with("a.xml", "foto.jpg"))
    assert found > 0 and checks == [("ok", "")]


def test_a_broken_zip_is_an_integrity_error_and_is_not_a_capture_but_the_file_stays(
    con: Connection, settings: Settings
) -> None:
    found, checks = extract(con, settings, zip_with("a.xml")[:-30])
    assert found == -1
    assert checks[0][0] == "error" and "zip inválido" in checks[0][1] and "secao=1" in checks[0][1]
    assert scalar(con, "SELECT COUNT(*) FROM metadata.captures") == 0
    assert len(list(settings.landing_dir.rglob("*.zip"))) == 1  # evidência para auditoria


def test_an_html_page_in_place_of_the_zip_is_rejected(con: Connection, settings: Settings) -> None:
    found, checks = extract(con, settings, b"<!DOCTYPE html><html>Acesso negado</html>")
    assert found == -1 and "página HTML" in checks[0][1]


def test_a_zip_without_the_expected_members_is_rejected(con: Connection, settings: Settings) -> None:
    found, checks = extract(con, settings, zip_with("foto.jpg", "outra.png"))
    assert found == -1 and "nenhum membro *.xml" in checks[0][1]


def test_the_size_must_match_the_content_length_the_source_informed(
    con: Connection, settings: Settings
) -> None:
    content = zip_with("a.xml")
    found, checks = extract(con, settings, content, size=str(len(content) + 10))
    assert found == -1 and "a fonte informou" in checks[0][1]


def test_after_a_rejected_download_the_next_run_tries_again_and_can_succeed(
    con: Connection, settings: Settings
) -> None:
    assert extract(con, settings, b"<html>erro</html>")[0] == -1
    found, checks = extract(con, settings, zip_with("a.xml"))
    assert found > 0 and [c[0] for c in checks] == ["error", "ok"]
