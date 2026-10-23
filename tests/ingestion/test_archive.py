"""Pacote .zip lido no lugar, anos por passo e filtro de minimização (`only`)."""

import zipfile
from pathlib import Path

import pytest

from plataforma_dados.core import migrations
from plataforma_dados.core.settings import Settings
from plataforma_dados.core.warehouse import rows
from plataforma_dados.ingestion import landing, loader, read
from plataforma_dados.ingestion.contract import InvalidContract, SourceContract, load_contract

YAML = """
source: teste
power: judiciario
level: federal
access: {base_url: "http://exemplo", format: csv, delimiter: ";", encoding: latin-1}
datasets:
  eleicoes:
    url: "{base_url}/cand_{year}.zip"
    load: yearly
    first_year: 1998
    step: 4
    archive: zip
    member: "*_TUDO.csv"
    write: merge
    primary_key: [id]
    only: {cargo: ["FEDERAL", "SENADOR"]}
    columns: [id, nome, cargo]
"""
CSV = "id;nome;cargo;cpf\n1;JOSÉ;FEDERAL;111\n2;MARIA;ESTADUAL;222\n3;ANA;SENADOR;333\n"


def contract(tmp_path: Path, text: str = YAML) -> SourceContract:
    file = tmp_path / "teste.yml"
    file.write_text(text, encoding="utf-8")
    return load_contract(file)


def package(tmp_path: Path) -> Path:
    file = tmp_path / "cand_2022.zip"
    with zipfile.ZipFile(file, "w") as z:
        z.writestr("leiame.pdf", b"%PDF")
        z.writestr("cand_2022_SP.csv", "id;nome;cargo\n99;SO NO ESTADO;FEDERAL\n".encode("latin-1"))
        z.writestr("cand_2022_TUDO.csv", CSV.encode("latin-1"))
    return file


def test_reader_takes_only_the_member_that_matches_and_decodes_the_declared_encoding(tmp_path: Path) -> None:
    c = contract(tmp_path)
    found = list(read.records(package(tmp_path), c, c.datasets["eleicoes"]))
    assert [r["nome"] for r in found] == ["JOSÉ", "MARIA", "ANA"]


def test_only_keeps_the_declared_rows_in_the_raw_and_the_columns_exclude_what_is_not_listed(
    tmp_path: Path,
) -> None:
    c = contract(tmp_path)
    settings = Settings(storage_root=tmp_path / "store")
    con = migrations.open_warehouse(settings)
    stats = loader.load_file(settings, c, c.datasets["eleicoes"], package(tmp_path), 1, con)
    assert stats == {"read": 3, "loaded": 2, "rejected": 0}  # MARIA (estadual) fica de fora
    found = rows(con, f"SELECT id, nome FROM {c.schema}.eleicoes ORDER BY id")
    assert [(r["id"], r["nome"]) for r in found] == [("1", "JOSÉ"), ("3", "ANA")]
    assert "cpf" not in {
        r["column_name"] for r in rows(con, "SELECT column_name FROM information_schema.columns")
    }


def test_years_follow_the_step_from_the_first_year(tmp_path: Path) -> None:
    c = contract(tmp_path)
    found = [year for _, year in landing.plan_historical(c, 1996, 2027)]
    assert found == [1998, 2002, 2006, 2010, 2014, 2018, 2022, 2026]


def test_step_needs_a_first_year_and_the_archive_must_be_known(tmp_path: Path) -> None:
    with pytest.raises(InvalidContract, match="step exige first_year"):
        contract(tmp_path, YAML.replace("    first_year: 1998\n", ""))
    with pytest.raises(InvalidContract, match="archive"):
        contract(tmp_path, YAML.replace("archive: zip", "archive: rar"))
