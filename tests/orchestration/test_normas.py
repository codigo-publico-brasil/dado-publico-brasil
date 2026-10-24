"""Normas, vetos e Constituição: catálogo, relações, dispositivos vetados, votos sem ligação a pessoas e o texto classificado."""

from dado_publico_brasil.core.settings import Settings
from dado_publico_brasil.core.warehouse import Connection, columns, rows, scalar

Env = tuple[Connection, Settings]


def test_catalog_has_every_norm_with_the_official_page_and_the_popular_name(full: Env) -> None:
    con, _ = full
    found = con.execute(
        "SELECT tipo_sigla, numero, ano, assinada_em, apelido, ementa, ementa_oficial, fonte_url "
        "FROM marts.normas WHERE norma_id = 1001"
    ).fetchone()
    assert found is not None
    assert found[:2] == ("LEI-n", "14999") and found[2] == 2024 and str(found[3]) == "2024-06-28"
    assert found[4] == "Lei do Teste"
    assert found[5] == "Altera a lei complementar x." and found[6] == "ALTERA A LEI COMPLEMENTAR X."
    assert found[7] == "https://legis.senado.leg.br/norma/1001"
    assert scalar(con, "SELECT COUNT(*) FROM marts.normas") == 3  # inclui o decreto, que não é detalhado


def test_only_laws_amendments_and_provisional_measures_are_detailed_and_a_missing_list_is_tolerated(
    full: Env,
) -> None:
    con, _ = full
    detailed = {r["norma_id"] for r in rows(con, "SELECT DISTINCT norma_id FROM marts.normas_publicacoes")}
    assert detailed == {1001, 1002, 579494}  # o decreto 1003 não entra; a emenda 1002 não tem relações ("")
    assert scalar(con, "SELECT COUNT(*) FROM marts.normas_relacoes WHERE norma_id = 1002") == 0


def test_relations_say_what_changed_each_norm_and_publications_say_where_it_came_out(full: Env) -> None:
    con, _ = full
    found = con.execute(
        "SELECT tipo_relacao, norma_posterior_id, norma_posterior_nome, norma_posterior_assinada_em "
        "FROM marts.normas_relacoes WHERE norma_id = 1001"
    ).fetchall()
    assert [(f[0], f[1], f[2], str(f[3])) for f in found] == [
        (
            "Declaração de Alteração Permanente",
            1002,
            "Emenda Constitucional nº 99 de 15/02/2024",
            "2024-02-15",
        )
    ]
    publication = con.execute(
        "SELECT tipo_sigla, publicada_em, pagina, coluna, tem_texto FROM marts.normas_publicacoes WHERE norma_id = 1001"
    ).fetchone()
    assert publication is not None and (publication[0], str(publication[1]), publication[4]) == (
        "PUB",
        "2024-07-01",
        True,
    )


def test_a_veto_points_to_the_vetoed_matter_and_to_the_norm_that_came_out(full: Env) -> None:
    con, _ = full
    found = con.execute(
        "SELECT numero, ano, materia_vetada_sigla, materia_vetada_numero, norma_id, veto_total, recebido_em, "
        "quantidade_dispositivos, fonte_url FROM marts.vetos"
    ).fetchall()
    assert len(found) == 1
    numero, ano, sigla, materia, norma, total, recebido, quantidade, url = found[0]
    assert (numero, ano, sigla, materia, norma, total, str(recebido), quantidade) == (
        5,
        2024,
        "PLP",
        "700",
        1001,
        False,
        "2024-07-05",
        2,
    )
    assert url.endswith("/materia/8001")


def test_vetoed_provisions_keep_the_text_the_reason_and_the_decision_as_the_source_says(full: Env) -> None:
    con, _ = full
    found = con.execute(
        "SELECT dispositivo_id, veto_id, texto_vetado, razao_veto, situacao, possui_votos, tipo_votacao, sessao_em "
        "FROM marts.dispositivos_vetados ORDER BY dispositivo_id"
    ).fetchall()
    assert [(f[0], f[1], f[4], f[5], f[6], str(f[7])) for f in found] == [
        (9001, 7001, "Rejeitado", True, "Painel", "2024-09-10"),
        (9002, 7001, "Não Apreciado", False, None, "None"),
    ]
    assert (
        found[0][2] == "Texto que foi vetado."
        and found[0][3] == "A proposição contraria o interesse público."
    )


def test_veto_votes_come_with_name_party_and_state_and_are_not_linked_to_people(full: Env) -> None:
    con, _ = full
    found = con.execute(
        "SELECT casa, nome_parlamentar, partido, uf, voto FROM marts.votos_em_vetos ORDER BY casa, nome_parlamentar"
    ).fetchall()
    assert found == [
        ("Câmara", "Bia", "BBB", "RJ", "Sim"),
        ("Câmara", "Carlos", "CCC", "MG", "Não"),
        ("Senado", "Beto Barreiras", "AAA", "SP", "Sim"),
    ]
    assert "id_pessoa" not in columns(
        con, "marts", "votos_em_vetos"
    )  # a fonte não traz o código do parlamentar


def test_the_norm_a_matter_generated_points_to_the_catalog(full: Env) -> None:
    con, _ = full
    assert scalar(con, "SELECT COUNT(*) FROM marts.normas_geradas WHERE norma_id IS NOT NULL") >= 1


def test_the_constitution_is_classified_with_the_context_of_each_provision(full: Env) -> None:
    con, _ = full
    found = {
        r["identificador"]: r["tipo"]
        for r in rows(
            con,
            "SELECT identificador, tipo FROM marts.constituicao_dispositivos "
            "WHERE parte = 'Constituição' AND identificador IS NOT NULL",
        )
    }
    assert found == {
        "Art. 1": "artigo",
        "Art. 1, I": "inciso",
        "Art. 1, II": "inciso",
        "Art. 1, parágrafo único": "parágrafo",
        "Art. 6": "artigo",
        "Art. 7": "artigo",
        "Art. 7, I": "inciso",
        "Art. 7, I, a)": "alínea",
        "Art. 7, § 1": "parágrafo",
        "Art. 8": "artigo",
    }
    chapter = con.execute(
        "SELECT titulo, capitulo FROM marts.constituicao_dispositivos WHERE identificador = 'Art. 6' AND parte = 'Constituição'"
    ).fetchone()
    assert chapter == ("TÍTULO I DOS PRINCÍPIOS FUNDAMENTAIS", "CAPÍTULO II DOS DIREITOS SOCIAIS")


def test_the_file_header_the_preamble_and_the_signatures_have_no_provision_context(full: Env) -> None:
    con, _ = full
    found = {
        r["tipo"]: r["artigo"]
        for r in rows(
            con,
            "SELECT tipo, artigo FROM marts.constituicao_dispositivos "
            "WHERE parte = 'Constituição' AND tipo IN ('cabeçalho do arquivo', 'preâmbulo', 'assinaturas')",
        )
    }
    assert found == {"cabeçalho do arquivo": None, "preâmbulo": None, "assinaturas": None}
    assert (
        scalar(
            con,
            "SELECT COUNT(DISTINCT atualizada_ate_emenda) FROM marts.constituicao_dispositivos WHERE parte = 'Constituição'",
        )
        == 1
    )
    assert (
        scalar(
            con,
            "SELECT MAX(atualizada_ate_emenda) FROM marts.constituicao_dispositivos WHERE parte = 'Constituição'",
        )
        == 99
    )


def test_amendment_notes_become_rows_with_kind_number_and_year_only_when_one_amendment_is_cited(
    full: Env,
) -> None:
    con, _ = full
    found = con.execute(
        "SELECT identificador, tipo_alteracao, emenda_numero, emenda_ano FROM marts.constituicao_alteracoes "
        "WHERE parte = 'Constituição' ORDER BY ordem, emenda_numero"
    ).fetchall()
    assert found == [
        ("Art. 6", "redação dada", 99, 2024),
        ("Art. 7, § 1", "incluído", 20, None),  # "nºs 20 e 41": duas emendas, o ano fica vazio
        ("Art. 7, § 1", "incluído", 41, None),
        ("Art. 8", "revogado", 98, 2023),
    ]


def test_the_cross_check_against_the_senate_reports_amendments_the_text_cites_and_the_senate_does_not(
    full: Env,
) -> None:
    con, _ = full
    unknown = scalar(
        con,
        "SELECT failures FROM metadata.dbt_results WHERE unique_id LIKE '%emendas_do_texto_desconhecidas_do_senado%'",
    )
    assert (
        unknown == 2
    )  # 20 e 41 não constam como alteração permanente no Senado; a 97 (só no Senado) é esperada
    beyond = scalar(
        con,
        "SELECT failures FROM metadata.dbt_results WHERE unique_id LIKE '%constituicao_cita_emenda_posterior%'",
    )
    assert beyond == 0


def test_the_catalog_gap_is_measured_when_the_year_of_a_detailed_norm_is_not_loaded(full: Env) -> None:
    con, _ = full
    missing = scalar(
        con,
        "SELECT failures FROM metadata.dbt_results WHERE unique_id LIKE '%relacoes_de_norma_fora_do_catalogo%'",
    )
    assert missing == 1  # a Constituição (1988) não está nos anos carregados
