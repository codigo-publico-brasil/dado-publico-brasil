"""Marts (entidades prontas para consumo) e o que as camadas anteriores entregam a eles."""

from dado_publico_brasil.core.settings import Settings
from dado_publico_brasil.core.warehouse import Connection, columns, scalar, tables


def person_id(con: Connection, name: str) -> int:
    return int(scalar(con, "SELECT id_pessoa FROM marts.pessoas WHERE nome = ?", (name,)))


def test_person_has_counts_last_party_search_keys_and_standardized_names(
    full: tuple[Connection, Settings],
) -> None:
    con, _ = full
    row = con.execute(
        "SELECT nome, nome_civil, nome_ordem, nome_busca, qtd_propostas, qtd_votos, ultimo_partido, "
        "ultima_uf, profissoes, primeira_legislatura_com_voto, foto_url, dt_nascimento, "
        "dt_captura IS NOT NULL FROM marts.pessoas WHERE nome = 'Ana Árvore'"
    ).fetchone()
    assert row is not None
    assert tuple(row[:12]) == (
        "Ana Árvore",
        "Ana da Silva",
        "ana arvore",
        "ana arvore ana da silva",
        4,
        2,
        "BBB",
        "SP",
        "Advogada",
        57,
        "http://foto/10.jpg",
        __import__("datetime").date(1980, 2, 3),
    )
    assert row[12] is True


def test_proposition_keeps_official_and_standardized_summary_and_the_source_url(
    full: tuple[Connection, Settings],
) -> None:
    con, _ = full
    assert con.execute(
        "SELECT sigla, ementa, ementa_oficial, situacao, fonte_url FROM marts.proposicoes "
        "WHERE id_proposicao = '102'"
    ).fetchone() == (
        "PL 9/2019",
        "Requer o desarquivamento de proposições.",
        "REQUER O DESARQUIVAMENTO DE PROPOSIÇÕES.",
        None,
        "https://www.camara.leg.br/proposicoesWeb/fichadetramitacao?idProposicao=102",
    )
    assert con.execute(
        "SELECT situacao, orgao_ultimo_status FROM marts.proposicoes WHERE id_proposicao = '100'"
    ).fetchone() == ("Aguardando Parecer", "CCJC")


def test_authorship_counts_the_authors_and_leaves_out_authors_that_are_not_people(
    full: tuple[Connection, Settings],
) -> None:
    con, _ = full
    ana = person_id(con, "Ana Árvore")
    rows = con.execute(
        "SELECT id_proposicao, ordem_assinatura, qtd_autores, proponente FROM marts.proposicoes_autorias "
        "WHERE id_pessoa = ? ORDER BY id_proposicao",
        (ana,),
    ).fetchall()
    assert rows == [("100", 1, 3, 1), ("101", 1, 2, 1), ("102", 1, 1, 1), ("999", 1, 1, 1)]
    senate = con.execute(
        "SELECT COUNT(*) FROM intermediate.int_proposicoes_autorias_ligadas "
        "WHERE id_proposicao = 100 AND id_pessoa IS NULL AND nome_autor = 'Senado Federal'"
    ).fetchone()
    assert senate == (1,)
    kept = con.execute(
        "SELECT COUNT(*) FROM marts.proposicoes_autorias WHERE id_proposicao = '100' AND id_pessoa IS NULL AND nome_autor = 'Senado Federal'"
    ).fetchone()
    assert kept == (1,)  # o autor que não é pessoa fica no mart, sem id_pessoa


def test_voting_lists_the_propositions_and_the_official_result(
    full: tuple[Connection, Settings],
) -> None:
    con, _ = full
    assert con.execute(
        "SELECT descricao, aprovada, votos_sim, votos_nao, proposicoes FROM marts.votacoes "
        "WHERE id_votacao = '100-1'"
    ).fetchone() == ("Aprovada a PEC.", 1, 2, 1, "PEC 5/2024")


def test_votes_carry_the_party_and_state_of_the_day(full: tuple[Connection, Settings]) -> None:
    con, _ = full
    ana = person_id(con, "Ana Árvore")
    assert con.execute(
        "SELECT voto, partido, uf FROM marts.votacoes_votos WHERE id_pessoa = ? ORDER BY dt_voto DESC",
        (ana,),
    ).fetchall() == [("Não", "BBB", "SP"), ("Sim", "AAA", "SP")]


def test_mandate_comes_from_observed_votes_and_official_dates_stay_empty(
    full: tuple[Connection, Settings],
) -> None:
    con, _ = full
    ana = person_id(con, "Ana Árvore")
    row = con.execute(
        "SELECT cargo, casa, id_legislatura, uf, dt_inicio, dt_fim, base FROM marts.mandatos WHERE id_pessoa = ?",
        (ana,),
    ).fetchone()
    assert row == (
        "Deputado federal",
        "Câmara dos Deputados",
        57,
        "SP",
        None,
        None,
        "votos observados",
    )


def test_staging_does_not_join_and_keeps_one_row_per_raw_row(
    full: tuple[Connection, Settings],
) -> None:
    con, _ = full
    assert scalar(con, "SELECT COUNT(*) FROM staging.stg_camara__votos") == scalar(
        con, "SELECT COUNT(*) FROM raw_federal_camara.votacoes_votos"
    )


def test_every_warehouse_table_of_the_marts_has_a_declared_contract(
    full: tuple[Connection, Settings],
) -> None:
    con, _ = full
    assert tables(con, "marts") == [
        "candidaturas",
        "candidaturas_bens",
        "candidaturas_votos",
        "constituicao_alteracoes",
        "constituicao_dispositivos",
        "emendas",
        "emendas_convenios",
        "emendas_favorecidos",
        "frentes",
        "frentes_membros",
        "legislaturas",
        "mandatos",
        "mandatos_exercicios",
        "normas",
        "normas_geradas",
        "normas_publicacoes",
        "normas_relacoes",
        "orgaos",
        "orgaos_membros",
        "partidos",
        "partidos_linhagem",
        "pessoas",
        "pessoas_fusoes",
        "pessoas_ocupacoes",
        "proposicoes",
        "proposicoes_autorias",
        "proposicoes_tramitacoes",
        "vetos",
        "vetos_dispositivos",
        "vetos_votos",
        "votacoes",
        "votacoes_votos",
    ]
    assert columns(con, "marts", "votacoes_votos") == [
        "fonte",
        "id_pessoa",
        "id_votacao",
        "voto",
        "dt_voto",
        "partido",
        "uf",
    ]


def test_descriptions_are_persisted_in_the_warehouse_for_tables_and_columns(
    full: tuple[Connection, Settings],
) -> None:
    con, _ = full
    table = scalar(
        con, "SELECT comment FROM duckdb_tables() WHERE schema_name='marts' AND table_name='votacoes_votos'"
    )
    column = scalar(
        con,
        "SELECT comment FROM duckdb_columns() "
        "WHERE schema_name='marts' AND table_name='votacoes_votos' AND column_name='id_votacao'",
    )
    assert table and "Voto de cada pessoa" in table
    assert column


def test_organs_and_fronts_link_members_to_people_and_report_unknown_deputies(
    full: tuple[Connection, Settings],
) -> None:
    con, _ = full
    assert scalar(con, "SELECT count(*) FROM marts.orgaos") == 2
    members = con.execute(
        "SELECT p.nome, m.cargo, m.dt_fim FROM marts.orgaos_membros m JOIN marts.pessoas p USING (id_pessoa) "
        "ORDER BY p.nome, m.dt_fim NULLS FIRST"
    ).fetchall()
    # as duas linhas distintas da fonte para a mesma pessoa e cargo são mantidas; o deputado 99 fica de fora
    assert [(r[0], r[1]) for r in members] == [("Ana Árvore", "Presidente")] * 2 + [("Bia", "Titular")]
    front = con.execute(
        "SELECT titulo, situacao, id_pessoa_coordenador IS NOT NULL FROM marts.frentes"
    ).fetchall()
    assert front == [("Frente X", "Em andamento", True)]
    assert scalar(con, "SELECT count(*) FROM marts.frentes_membros") == 2


def test_official_legislature_dates_do_not_become_the_mandate_dates(
    full: tuple[Connection, Settings],
) -> None:
    con, _ = full
    row = con.execute(
        "SELECT dt_inicio, dt_fim, dt_legislatura_inicio, dt_legislatura_fim FROM marts.mandatos WHERE id_legislatura = 57 LIMIT 1"
    ).fetchone()
    assert row is not None
    assert row[0] is None and row[1] is None
    assert str(row[2]) == "2023-02-01" and str(row[3]) == "2027-01-31"


def test_photo_comes_from_the_fronts_when_the_person_has_no_vote_photo(
    full: tuple[Connection, Settings],
) -> None:
    con, _ = full
    assert scalar(con, "SELECT foto_url FROM marts.pessoas WHERE nome = 'Bia'") == "http://foto/11.jpg"


def test_party_lineage_comes_from_the_curated_table_and_every_event_cites_the_official_page(
    full: tuple[Connection, Settings],
) -> None:
    con, _ = full
    found = con.execute(
        "SELECT sigla_anterior, sigla_posterior, tipo, ano FROM marts.partidos_linhagem "
        "WHERE sigla_anterior = 'PMDB'"
    ).fetchall()
    assert found == [("PMDB", "MDB", "mudança de nome", 2018)]
    assert (
        scalar(
            con,
            "SELECT COUNT(*) FROM marts.partidos_linhagem WHERE fonte_url NOT LIKE 'https://%tse.jus.br/%'",
        )
        == 0
    )
