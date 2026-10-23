"""Funções de padronização de texto (macros nativas do DuckDB em `dbt/macros`)."""

from pathlib import Path

import duckdb
import pytest

MACROS = Path(__file__).resolve().parents[2] / "dbt" / "macros" / "text_functions.sql"


@pytest.fixture(scope="module")
def db() -> duckdb.DuckDBPyConnection:
    body = MACROS.read_text(encoding="utf-8").split("{% macro create_text_functions() %}")[1]
    connection = duckdb.connect()
    connection.execute(body.split("{% endmacro %}")[0])
    return connection


def one(db: duckdb.DuckDBPyConnection, sql: str, *args: object) -> object:
    row = db.execute(sql, list(args)).fetchone()
    assert row is not None
    return row[0]


@pytest.mark.parametrize(
    ("original", "expected"),
    [
        ("REGINALDO LÁZARO DE OLIVEIRA LOPES", "Reginaldo Lázaro de Oliveira Lopes"),
        ("CARNEIRO DA CUNHA", "Carneiro da Cunha"),
        ("maria dos santos", "Maria dos Santos"),
        ("Reginaldo Lopes", "Reginaldo Lopes"),
        ("João da Silva Neto", "João da Silva Neto"),
        ("JHC", "JHC"),
        ("PEDRO II", "Pedro II"),
        ("D'ÁVILA E SILVA", "D'Ávila e Silva"),
        ("ANA-MARIA LIMA", "Ana-Maria Lima"),
        ("  JOAO   ROMA ", "Joao Roma"),
    ],
)
def test_proper_name_only_changes_single_case_text(
    db: duckdb.DuckDBPyConnection, original: str, expected: str
) -> None:
    assert one(db, "SELECT proper_name(?)", original) == expected


def test_proper_name_of_empty_or_null_is_null(db: duckdb.DuckDBPyConnection) -> None:
    assert one(db, "SELECT proper_name(NULL)") is None
    assert one(db, "SELECT proper_name('   ')") is None


def test_sentence_case(db: duckdb.DuckDBPyConnection) -> None:
    assert one(db, "SELECT sentence_case(?)", "COMISSÃO PERMANENTE") == "Comissão permanente"
    assert one(db, "SELECT sentence_case(?)", "Órgão do Poder Executivo") == "Órgão do Poder Executivo"


def test_standardize_summary_keeps_known_acronyms_and_sentence_starts(
    db: duckdb.DuckDBPyConnection,
) -> None:
    text = "REQUER AO BNDES INFORMAÇÕES. DISPÕE SOBRE O ASSUNTO"
    result = one(db, "SELECT standardize_summary(?, ['BNDES'])", text)
    assert result == "Requer ao BNDES informações. Dispõe sobre o assunto"


def test_standardize_summary_leaves_mixed_case_alone_and_capitalizes_lowercase(
    db: duckdb.DuckDBPyConnection,
) -> None:
    mixed = "Altera a Lei nº 11.340, de 2006."
    assert one(db, "SELECT standardize_summary(?, []::varchar[])", mixed) == mixed
    lower = "requer o desarquivamento de proposições."
    assert one(db, "SELECT standardize_summary(?, []::varchar[])", lower) == (
        "Requer o desarquivamento de proposições."
    )


def test_name_key_compares_names_across_sources(db: duckdb.DuckDBPyConnection) -> None:
    assert one(db, "SELECT name_key(?)", "  José   da  SILVA ") == "jose da silva"
    assert one(db, "SELECT name_key(?)", "Jose da Silva") == one(db, "SELECT name_key(?)", "JOSÉ DA SILVA")
    assert one(db, "SELECT name_key(NULL)") is None
    assert one(db, "SELECT name_key('   ')") is None
