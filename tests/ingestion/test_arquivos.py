"""Materialização de arquivos (ADR 0037): idempotente, atômica, tolerante a captura ruim; regex das fotos do TSE."""

import re
import zipfile
from pathlib import Path

import duckdb
import pytest

from dado_publico_brasil.core.settings import DBT_DIR, Settings
from dado_publico_brasil.core.warehouse import Connection, rows
from dado_publico_brasil.ingestion import arquivos, landing
from dado_publico_brasil.ingestion import contract as contracts

SPEC = r"""
source: teste
power: legislativo
level: federal
description: Fonte de teste
access: {base_url: "http://exemplo", delimiter: ",", encoding: utf-8}
datasets:
  fotos:
    url: "{base_url}/fotos-{year}.zip"
    load: yearly
    archive: zip
    raw: false
    files: {collection: fotos, member: '^(?P<x>.+)\.jpg$', path: "{partition}/{x}.jpg"}
"""


def contract_from(tmp_path: Path) -> contracts.SourceContract:
    file = tmp_path / "teste.yml"
    file.write_text(SPEC, encoding="utf-8")
    return contracts.load_contract(file)


def land(
    con: Connection, settings: Settings, name: str, members: dict[str, bytes] | None, part: int = 2022
) -> None:
    file = settings.landing_dir / "teste" / "fotos" / name
    file.parent.mkdir(parents=True, exist_ok=True)
    if members is None:
        file.write_bytes(b"isto nao e um zip")
    else:
        with zipfile.ZipFile(file, "w") as package:
            for member, content in members.items():
                package.writestr(member, content)
    landing.register_capture(
        con, "teste", "fotos", part, f"https://exemplo/fotos-{part}.zip", name, file.stat().st_size,
        file.relative_to(settings.storage_root).as_posix(), 0,
    )  # fmt: skip


def files(settings: Settings) -> list[str]:
    base = settings.storage_root / "arquivos"
    return sorted(p.relative_to(base).as_posix() for p in base.rglob("*") if p.is_file())


def test_a_path_that_leaves_the_collection_is_refused_and_does_not_stop_the_other_captures(
    con: Connection, settings: Settings, tmp_path: Path
) -> None:
    spec = contract_from(tmp_path)
    land(con, settings, "mau.zip", {"../../fora.jpg": b"x"}, 2018)
    land(con, settings, "bom.zip", {"a.jpg": b"ok"}, 2022)
    with pytest.warns(UserWarning, match="sai da coleção"):
        assert arquivos.materialize(con, settings, spec) == 1
    assert files(settings) == ["legislativo/federal/teste/arq_fotos/2022/a.jpg"]


def test_a_corrupt_zip_is_warned_about_and_the_rest_goes_on(
    con: Connection, settings: Settings, tmp_path: Path
) -> None:
    spec = contract_from(tmp_path)
    land(con, settings, "quebrado.zip", None, 2018)
    land(con, settings, "bom.zip", {"a.jpg": b"ok"}, 2022)
    with pytest.warns(UserWarning, match="captura"):
        assert arquivos.materialize(con, settings, spec) == 1
    assert len(files(settings)) == 1


def test_writes_are_atomic_idempotent_and_a_vanished_member_keeps_its_last_copy(
    con: Connection, settings: Settings, tmp_path: Path
) -> None:
    spec = contract_from(tmp_path)
    land(con, settings, "v1.zip", {"a.jpg": b"um", "b.jpg": b"dois"})
    assert arquivos.materialize(con, settings, spec) == 2
    assert arquivos.materialize(con, settings, spec) == 0
    assert not [f for f in files(settings) if f.endswith(".parte")]
    # captura nova da mesma URL em que o membro b sumiu. Comportamento documentado: a última cópia materializada
    # de b permanece, com a captura de origem anterior em metadata.arquivos.
    land(con, settings, "v2.zip", {"a.jpg": b"UM!"})
    assert arquivos.materialize(con, settings, spec) == 1
    assert len(files(settings)) == 2
    found = rows(con, "SELECT caminho, id_captura FROM metadata.arquivos ORDER BY caminho")
    assert found[0]["id_captura"] > found[1]["id_captura"]


@pytest.mark.parametrize(
    "member, uf, ext",
    [("FBR280001_div.jpg", "BR", "jpg"), ("BR280001_div.jpg", "BR", "jpg"), ("FRJ1001_div.jpeg", "RJ", "jpeg"),
     ("FSP5_div.png", "SP", "png")],
)  # fmt: skip
def test_the_tse_member_pattern_and_the_mart_agree_on_the_state_folder(
    member: str, uf: str, ext: str
) -> None:
    pattern = contracts.find("tse").datasets["fotos_br"].files
    assert pattern is not None and pattern.member
    found = re.match(pattern.member, member)
    assert found and (found["uf"], found["ext"]) == (uf, ext)
    mem = duckdb.connect()
    sql = (DBT_DIR / "models/marts/eleicoes/fct_candidaturas.sql").read_text(encoding="utf-8")
    assert "regexp_extract(f.arquivo, '^F?([A-Z]{2})', 1)" in sql
    assert mem.execute(f"SELECT regexp_extract('{member}', '^F?([A-Z]{{2}})', 1)").fetchone() == (uf,)
    assert mem.execute(f"SELECT regexp_extract('{member}', '[.](jpe?g|png)$', 1)").fetchone() == (ext,)


def test_a_new_capture_does_not_rewrite_a_member_whose_file_already_has_the_same_size(
    con: Connection, settings: Settings, tmp_path: Path
) -> None:
    spec = contract_from(tmp_path)
    land(con, settings, "v1.zip", {"a.jpg": b"um", "b.jpg": b"dois"})
    arquivos.materialize(con, settings, spec)
    target = settings.storage_root / "arquivos/legislativo/federal/teste/arq_fotos/2022/a.jpg"
    before = target.stat().st_mtime_ns
    old = rows(con, "SELECT sha256_arquivo FROM metadata.arquivos WHERE caminho = '2022/a.jpg'")[0]
    land(con, settings, "v2.zip", {"a.jpg": b"um", "b.jpg": b"DOIS!"})  # a: mesmo tamanho; b: mudou
    assert arquivos.materialize(con, settings, spec) == 1
    assert target.stat().st_mtime_ns == before
    found = {r["caminho"]: r for r in rows(con, "SELECT * FROM metadata.arquivos")}
    assert (
        found["2022/a.jpg"]["id_captura"] == found["2022/b.jpg"]["id_captura"]
    )  # aponta para a captura nova
    assert found["2022/a.jpg"]["sha256_arquivo"] == old["sha256_arquivo"]
