"""Emendas parlamentares (Portal da Transparência): valores, "sem informação" vazio e favorecido pessoa física descartado."""

from dado_publico_brasil.core.settings import Settings
from dado_publico_brasil.core.warehouse import Connection, columns, scalar

Env = tuple[Connection, Settings]


def test_the_three_tables_come_from_the_same_package(full: Env) -> None:
    con, _ = full
    assert scalar(con, "SELECT COUNT(*) FROM marts.emendas") == 3
    assert scalar(con, "SELECT COUNT(*) FROM marts.emendas_convenios") == 1
    assert scalar(con, "SELECT COUNT(*) FROM marts.emendas_favorecidos") == 4  # como a fonte publica


def test_values_become_numbers_and_no_information_becomes_empty(full: Env) -> None:
    con, _ = full
    found = con.execute(
        "SELECT emenda_codigo, ano, autor_codigo, autor_nome, municipio_ibge, valor_empenhado, valor_liquidado, "
        "valor_pago, valor_restos_a_pagar_pagos FROM marts.emendas ORDER BY ano, emenda_codigo NULLS FIRST"
    ).fetchall()
    old, individual, relator = found
    assert old[:5] == (None, 2014, None, None, 9999999) and float(old[8]) == 1000.0
    assert individual[:4] == ("202471280001", 2024, "7128", "Fulano de Tal")
    assert [float(v) for v in individual[5:8]] == [499995.0, 250000.5, 100000.0]
    assert relator[3] == "Relator Geral"


def test_amendments_are_not_linked_to_people_because_the_author_has_no_parliament_code(full: Env) -> None:
    con, _ = full
    assert "id_pessoa" not in columns(con, "marts", "emendas")


def test_every_favored_party_enters_as_published_and_the_rows_that_identify_a_person_are_flagged(
    full: Env,
) -> None:
    con, _ = full
    assert scalar(con, "SELECT COUNT(*) FROM raw_federal_transparencia.emendas_favorecidos") == 4
    found = {
        r[0]: r[1]
        for r in con.execute(
            "SELECT tipo_favorecido, contem_dado_pessoal FROM marts.emendas_favorecidos"
        ).fetchall()
    }
    assert found == {
        "Pessoa Jurídica": False,
        "Unidade Gestora": False,
        "Pessoa Fisica": True,  # CPF mascarado: cidadão comum
        "Inscrição Genérica": True,
    }
    assert (
        scalar(con, "SELECT COUNT(*) FROM marts.emendas_favorecidos WHERE favorecido_codigo LIKE '%*%'") == 1
    )


def test_the_table_with_personal_data_of_third_parties_is_classified_and_its_columns_are_marked(
    full: Env,
) -> None:
    from dado_publico_brasil.core.settings import Settings
    from dado_publico_brasil.transformation import catalog

    settings = Settings()
    sensitivity = {t["name"]: t["sensitivity"] for t in catalog.tables(settings) if t["schema"] == "marts"}
    assert sensitivity["emendas_favorecidos"] == "publico-dados-pessoais-de-terceiros"
    marked = {
        c["name"] for c in catalog.columns(settings) if c["table"] == "emendas_favorecidos" and c["pii"]
    }
    assert marked == {"favorecido", "favorecido_codigo"}


def test_the_missing_author_is_measured_as_a_gap(full: Env) -> None:
    con, _ = full
    assert (
        scalar(
            con,
            "SELECT failures FROM metadata.dbt_results WHERE unique_id LIKE '%emendas_sem_autor_conhecido%'",
        )
        == 1
    )


def test_a_convenio_keeps_the_date_object_and_value(full: Env) -> None:
    con, _ = full
    found = con.execute("SELECT publicado_em, convenente, valor FROM marts.emendas_convenios").fetchone()
    assert found is not None and str(found[0]) == "2025-01-06" and float(found[2]) == 1450000.0
