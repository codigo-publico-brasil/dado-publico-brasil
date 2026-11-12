"""Emendas parlamentares (Portal da Transparência): valores, "sem informação" vazio e favorecido pessoa física descartado."""

from dado_publico_brasil.core.settings import Settings
from dado_publico_brasil.core.warehouse import Connection, scalar

Env = tuple[Connection, Settings]


def test_the_three_tables_come_from_the_same_package(full: Env) -> None:
    con, _ = full
    assert scalar(con, "SELECT COUNT(*) FROM marts.fct_emendas") == 4
    assert scalar(con, "SELECT COUNT(*) FROM marts.fct_emendas_convenios") == 1
    assert scalar(con, "SELECT COUNT(*) FROM marts.fct_emendas_favorecidos") == 4  # como a fonte publica


def test_values_become_numbers_and_no_information_becomes_empty(full: Env) -> None:
    con, _ = full
    found = con.execute(
        "SELECT cd_emenda, ano, cd_autor, autor_nome, municipio_ibge, valor_empenhado, valor_liquidado, "
        "valor_pago, valor_restos_a_pagar_pagos FROM marts.fct_emendas ORDER BY ano, cd_emenda NULLS FIRST"
    ).fetchall()
    old, individual, unmatched, relator = found
    assert old[:5] == (None, 2014, None, None, 9999999) and float(old[8]) == 1000.0
    assert individual[:4] == ("202471280001", 2024, "7128", "Ana Arvore")
    assert [float(v) for v in individual[5:8]] == [499995.0, 250000.5, 100000.0]
    assert relator[3] == "Relator Geral"


def test_an_individual_amendment_is_linked_to_the_one_person_with_that_name_in_office(full: Env) -> None:
    con, _ = full
    found = {
        r[0]: r[1:]
        for r in con.execute(
            "SELECT cd_emenda, id_pessoa, regra_ligacao_pessoa, precisao_ligacao_pessoa FROM marts.fct_emendas "
            "WHERE cd_emenda IS NOT NULL"
        ).fetchall()
    }
    ana = scalar(con, "SELECT id_pessoa FROM marts.dim_pessoas WHERE nome_civil = 'Ana da Silva'")
    assert found["202471280001"] == (ana, "nome_parlamentar_e_exercicio", "derivada")


def test_what_does_not_match_stays_without_person_and_without_rule(full: Env) -> None:
    con, _ = full
    # sem correspondência, de relator e sem autor: nunca ligados; o regra e a precisão vão vazias juntas
    assert con.execute(
        "SELECT cd_emenda, id_pessoa, regra_ligacao_pessoa, precisao_ligacao_pessoa FROM marts.fct_emendas "
        "WHERE cd_emenda IS DISTINCT FROM '202471280001' ORDER BY cd_emenda NULLS FIRST"
    ).fetchall() == [
        (None, None, None, None),
        ("202480010001", None, None, None),
        ("202490020001", None, None, None),
    ]


def test_individual_amendments_without_person_are_measured_as_a_gap(full: Env) -> None:
    con, _ = full
    assert (
        scalar(
            con,
            "SELECT qtd_falhas FROM metadata.testes_resultados "
            "WHERE id_no LIKE '%emendas_individuais_sem_pessoa%'",
        )
        == 1
    )


def test_every_favored_party_enters_as_published_and_the_rows_that_identify_a_person_are_flagged(
    full: Env,
) -> None:
    con, _ = full
    assert scalar(con, "SELECT COUNT(*) FROM raw_federal_transparencia.emendas_favorecidos") == 4
    found = {
        r[0]: r[1]
        for r in con.execute(
            "SELECT tipo_favorecido, fl_contem_dado_pessoal FROM marts.fct_emendas_favorecidos"
        ).fetchall()
    }
    assert found == {
        "Pessoa Jurídica": False,
        "Unidade Gestora": False,
        "Pessoa Fisica": True,  # CPF mascarado: cidadão comum
        "Inscrição Genérica": True,
    }
    assert (
        scalar(con, "SELECT COUNT(*) FROM marts.fct_emendas_favorecidos WHERE cd_favorecido LIKE '%*%'") == 1
    )


def test_the_table_with_personal_data_of_third_parties_is_classified_and_its_columns_are_marked(
    full: Env,
) -> None:
    from dado_publico_brasil.core.settings import Settings
    from dado_publico_brasil.transformation import catalog

    settings = Settings()
    sensitivity = {t["name"]: t["sensitivity"] for t in catalog.tables(settings) if t["schema"] == "marts"}
    assert sensitivity["fct_emendas_favorecidos"] == "publico-dados-pessoais-de-terceiros"
    marked = {
        c["name"] for c in catalog.columns(settings) if c["table"] == "fct_emendas_favorecidos" and c["pii"]
    }
    assert marked == {"favorecido", "cd_favorecido"}


def test_the_missing_author_is_measured_as_a_gap(full: Env) -> None:
    con, _ = full
    assert (
        scalar(
            con,
            "SELECT qtd_falhas FROM metadata.testes_resultados WHERE id_no LIKE '%emendas_sem_autor_conhecido%'",
        )
        == 1
    )


def test_a_convenio_keeps_the_date_object_and_value(full: Env) -> None:
    con, _ = full
    found = con.execute("SELECT dt_publicacao, convenente, valor FROM marts.fct_emendas_convenios").fetchone()
    assert found is not None and str(found[0]) == "2025-01-06" and float(found[2]) == 1450000.0
