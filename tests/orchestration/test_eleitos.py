"""Eleitos das eleições gerais: quem foi eleito, o estado de cada cargo e o que cada eleito declarou na campanha.

O conjunto sintético de 2022 tem: BIA SOUZA (deputada federal do RJ, ligada à pessoa, com votos, bens, receitas e despesas)
e CARLOS ELEITO (deputado federal de MG, sem vínculo e sem votos nem contas). Vagas: RJ 1 de 1, MG 1 de 2 e senador de SP
0 de 2. O deputado estadual eleito não é dos cargos desta página.
"""

from decimal import Decimal

from dado_publico_brasil.core.settings import Settings
from dado_publico_brasil.core.warehouse import Connection, rows, scalar


def test_the_elected_of_every_office_include_the_ones_without_a_link_and_state_deputies_have_no_mandate_type(
    full: tuple[Connection, Settings],
) -> None:
    con, _ = full
    found = rows(
        con,
        "SELECT nome, cargo, uf, resultado, qtd_votos, percentual_votos_nominais, id_pessoa IS NOT NULL AS ligado, "
        "tipo_mandato, vinculo_metodo, ue, ue_nome FROM marts.eleitos WHERE ano_eleicao = 2022 ORDER BY nome",
    )
    assert [r["nome"] for r in found] == [
        "Bia Souza",
        "Carlos Eleito",
        "Fulano Estadual",
        "Governo Reeleito",
        "Prefeito Eleito",
        "Vereador Dois",
        "Vereador Media",
        "Vereadora Um",
    ]  # sem o prefeito da eleição suplementar nem o vereador não eleito
    bia, carlos, fulano, governador, prefeito, *vereadores = found
    assert (bia["cargo"], bia["uf"], bia["resultado"], bia["ligado"]) == (
        "Deputado federal",
        "RJ",
        "Eleito por qp",
        True,
    )
    assert bia["vinculo_metodo"] == "nome civil e data de nascimento iguais e únicos"
    assert (bia["qtd_votos"], bia["percentual_votos_nominais"]) == (1750, Decimal("100.00"))
    assert bia["tipo_mandato"] == "novato"  # o mandato dela começa depois dessa eleição: nenhum anterior
    assert (carlos["ligado"], carlos["qtd_votos"], carlos["percentual_votos_nominais"]) == (False, None, None)
    assert (
        carlos["tipo_mandato"] == "reeleito" and carlos["vinculo_metodo"] is None
    )  # prova do TSE: eleito em 2018 também
    assert (prefeito["cargo"], prefeito["ue"], prefeito["ue_nome"], prefeito["tipo_mandato"]) == (
        "Prefeito",
        "60011",
        "Municipio 60011",
        None,
    )
    assert {v["cargo"] for v in vereadores} == {"Vereador"}
    assert (fulano["cargo"], fulano["uf"], fulano["tipo_mandato"]) == (
        "Deputado estadual",
        "SP",
        None,
    )  # só em 2022 (em 2018 não foi eleito): sem prova no TSE, fica sem tipo
    assert (governador["cargo"], governador["tipo_mandato"]) == ("Governador", "reeleito")


def test_each_office_shows_its_real_state_without_guessing(full: tuple[Connection, Settings]) -> None:
    con, _ = full
    found = {
        (r["ue"], r["cargo"]): (r["qtd_vagas"], r["qtd_eleitos"], r["qtd_pendentes"], r["status"])
        for r in rows(
            con, "SELECT ue, cargo, qtd_vagas, qtd_eleitos, qtd_pendentes, status FROM marts.eleitos_cargos"
        )
    }
    assert found == {
        ("RJ", "Deputado federal"): (1, 1, 0, "eleito_provisorio"),
        ("MG", "Deputado federal"): (2, 1, 1, "aguardando_resultado"),
        ("SP", "Senador"): (2, 0, 2, "aguardando_resultado"),
        ("SP", "Deputado estadual"): (70, 1, 69, "aguardando_resultado"),
        ("60011", "Prefeito"): (1, 1, 0, "eleito_provisorio"),
        ("60011", "Vereador"): (3, 3, 0, "eleito_provisorio"),
        ("60012", "Vereador"): (3, 0, 3, "aguardando_resultado"),
    }


def test_the_campaign_has_only_totals_and_stays_empty_when_the_file_has_nothing_for_the_candidate(
    full: tuple[Connection, Settings],
) -> None:
    con, _ = full
    bia = rows(
        con,
        "SELECT qtd_bens, valor_bens, qtd_receitas, valor_receitas, qtd_despesas, valor_despesas FROM marts.eleitos_campanhas "
        "WHERE id_candidatura IN (SELECT id_candidatura FROM marts.eleitos WHERE nome = 'Bia Souza')",
    )[0]
    assert (bia["qtd_bens"], bia["valor_bens"]) == (2, Decimal("180000.50"))
    assert (bia["qtd_receitas"], bia["valor_receitas"]) == (2, Decimal("1250.50"))
    assert (bia["qtd_despesas"], bia["valor_despesas"]) == (1, Decimal("400.00"))
    carlos = rows(
        con,
        "SELECT qtd_bens, valor_receitas, valor_despesas FROM marts.eleitos_campanhas "
        "WHERE id_candidatura IN (SELECT id_candidatura FROM marts.eleitos WHERE nome = 'Carlos Eleito')",
    )[0]
    assert carlos == {"qtd_bens": None, "valor_receitas": None, "valor_despesas": None}


def test_the_campaign_finance_raw_keeps_no_name_or_document_of_donors_and_reads_only_the_candidate_files(
    full: tuple[Connection, Settings],
) -> None:
    con, _ = full
    columns = {
        r["column_name"]
        for r in rows(
            con,
            "SELECT column_name FROM duckdb_columns() WHERE schema_name = 'raw_federal_tse' "
            "AND table_name IN ('receitas_candidatos', 'despesas_candidatos')",
        )
    }
    assert (
        not {"nm_doador", "nr_cpf_cnpj_doador", "nm_fornecedor", "nr_cpf_cnpj_fornecedor", "nr_cpf_candidato"}
        & columns
    )
    # o arquivo de doador originário (mesmo pacote) não é lido: 3 receitas, e não 6
    assert scalar(con, "SELECT count(*) FROM raw_federal_tse.receitas_candidatos") == 3
    assert scalar(con, "SELECT count(*) FROM raw_federal_tse.despesas_candidatos") == 1


def test_every_elected_of_the_staging_reaches_the_mart(full: tuple[Connection, Settings]) -> None:
    con, _ = full
    assert scalar(
        con,
        "SELECT count(*) FROM staging.stg_tse__candidaturas WHERE resultado LIKE 'Eleito%' "
        "AND cargo IN ('Presidente', 'Governador', 'Senador', 'Deputado federal', 'Deputado estadual', 'Deputado distrital', 'Prefeito', 'Vereador') ",
    ) == scalar(con, "SELECT count(*) FROM marts.eleitos")


def test_the_same_person_is_found_across_tse_elections_only_when_name_and_birth_are_unique(
    full: tuple[Connection, Settings],
) -> None:
    con, _ = full
    ligados = {
        r["id_candidatura"]: r["id_pessoa_tse"]
        for r in rows(con, "SELECT * FROM intermediate.int_tse_pessoas")
    }
    carlos22 = next(k for k in ligados if k.startswith("2022:MG:") and k.endswith(":1005"))
    carlos18 = "2018:MG:2005"
    assert ligados[carlos22] == ligados[carlos18]  # mesmo nome civil e nascimento em 2018 e 2022
    roberto = {ligados[k] for k in ligados if k.endswith(":1003") or k.endswith(":1004")}
    assert (
        len(roberto) == 2
    )  # homônimos na mesma eleição: o nome civil não os junta (cada um fica com a sua chave de urna)
    assert not [
        k for k in ligados if k.endswith(":1001")
    ]  # nascimento em 1º de janeiro: o TSE usa para "só o ano"


def test_the_history_of_an_elected_has_his_earlier_candidacies_and_never_the_current_one(
    full: tuple[Connection, Settings],
) -> None:
    con, _ = full
    found = rows(
        con,
        "SELECT e.nome, h.ano_eleicao, h.cargo, h.resultado FROM marts.eleitos_historico h "
        "JOIN marts.eleitos e USING (id_candidatura) ORDER BY e.nome, h.ano_eleicao",
    )
    assert [(r["nome"], r["ano_eleicao"], r["cargo"], r["resultado"]) for r in found] == [
        ("Carlos Eleito", 2018, "Deputado federal", "Eleito por qp"),
        ("Fulano Estadual", 2018, "Deputado estadual", "Não eleito"),
        ("Governo Reeleito", 2018, "Governador", "Eleito"),
    ]


def test_who_changed_civil_name_is_linked_by_the_ballot_name_and_birth_date(
    full: tuple[Connection, Settings],
) -> None:
    con, _ = full
    ligacoes = {
        r["id_na_fonte"]: (r["id_pessoa"], r["metodo"])
        for r in rows(
            con, "SELECT id_na_fonte, id_pessoa, metodo FROM staging.stg_identity__pessoa_identificadores"
        )
        if str(r["id_na_fonte"]).startswith(("2018:SP:", "2022:SP:"))
    }
    ana18, ana22 = ligacoes["2018:SP:2007"], next(v for k, v in ligacoes.items() if k.endswith(":1002"))
    assert ana18[0] == ana22[0]  # mesma pessoa da Câmara, embora o nome civil de 2018 seja outro
    assert ana18[1] == "nome de urna e data de nascimento iguais e únicos"
    assert ana22[1] == "nome civil e data de nascimento iguais e únicos"  # a regra de base vale primeiro
    assert "2018:SP:2008" not in ligacoes  # o nome de urna dela não é o de nenhum parlamentar


def test_the_same_person_is_found_across_elections_also_by_the_ballot_name(
    full: tuple[Connection, Settings],
) -> None:
    con, _ = full
    ligados = {
        r["id_candidatura"]: r["id_pessoa_tse"]
        for r in rows(con, "SELECT * FROM intermediate.int_tse_pessoas")
    }
    ana22 = next(k for k in ligados if k.startswith("2022:SP:") and k.endswith(":1002"))
    assert ligados[ana22] == ligados["2018:SP:2008"]  # nome civil diferente, mesmo nome de urna e nascimento
    assert ligados["2018:SP:2007"] != ligados[ana22]  # outro nome civil e outro nome de urna: nada os liga


def test_tipo_mandato_for_the_other_offices_comes_only_from_the_tse_history_and_is_never_novato(
    full: tuple[Connection, Settings],
) -> None:
    con, _ = full
    types = dict(
        con.execute(
            "SELECT cargo, tipo_mandato FROM marts.eleitos WHERE ano_eleicao = 2022 "
            "AND cargo IN ('Governador', 'Prefeito', 'Vereador')"
        ).fetchall()
    )
    assert types["Governador"] == "reeleito"  # eleito em 2018 e em 2022, pela mesma pessoa do TSE
    assert types["Prefeito"] is None  # sem eleição anterior no TSE: nada é afirmado, e nunca vira novato
    assert types["Vereador"] is None
