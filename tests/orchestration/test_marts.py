"""Marts (entidades prontas para consumo) e o que as camadas anteriores entregam a eles."""

import datetime

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


def test_deputy_mandate_gets_its_start_from_the_official_history_and_has_no_end_while_in_progress(
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
        datetime.date(
            2023, 2, 3
        ),  # primeiro registro em exercício do histórico (não o início da legislatura)
        None,  # a licença não encerra o mandato; só o registro de fim de mandato
        "exercício oficial",
    )
    bia = person_id(con, "Bia")
    assert con.execute(
        "SELECT dt_inicio, base FROM marts.mandatos WHERE id_pessoa = ?", (bia,)
    ).fetchone() == (
        None,
        "votos observados",  # a fonte não tem histórico dela (404): fica vazio, nada é inferido
    )
    columns_in_raw = {r[0] for r in con.execute("DESCRIBE raw_federal_camara.deputados_historico").fetchall()}
    assert not {"email", "url_foto"} & columns_in_raw
    detail = {r[0] for r in con.execute("DESCRIBE raw_federal_camara.deputados_detalhe").fetchall()}
    assert (
        not {"cpf", "ultimo_status__email", "ultimo_status__url_foto"} & detail
    )  # só o gabinete institucional
    assert con.execute(
        "SELECT escolaridade, email_institucional, telefone_institucional, gabinete_endereco FROM marts.pessoas WHERE id_pessoa = ?",
        (ana,),
    ).fetchone() == ("Superior", "dep.ana@camara.leg.br", "3215-5979", "prédio 3, sala 979")


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
        "eleitos",
        "eleitos_campanhas",
        "eleitos_cargos",
        "eleitos_chapas",
        "eleitos_historico",
        "emendas",
        "emendas_convenios",
        "emendas_favorecidos",
        "frentes",
        "frentes_membros",
        "legislaturas",
        "mandatos",
        "mandatos_exercicios",
        "municipios",
        "municipios_codigos_tse",
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
    bia = person_id(con, "Bia")  # sem histórico na fonte: a data da legislatura não vira a do mandato
    row = con.execute(
        "SELECT dt_inicio, dt_fim, dt_legislatura_inicio, dt_legislatura_fim FROM marts.mandatos "
        "WHERE id_legislatura = 57 AND id_pessoa = ?",
        (bia,),
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
    changes = con.execute(
        "SELECT sigla_anterior, sigla_posterior, tipo, ano FROM marts.partidos_linhagem "
        "WHERE tipo = 'mudança de nome'"
    ).fetchall()
    assert changes  # a tabela curada traz mudanças de nome...
    assert all(before != after and year for before, after, _, year in changes)  # ...cada uma com o ano
    assert (
        scalar(
            con,
            "SELECT COUNT(*) FROM marts.partidos_linhagem WHERE fonte_url NOT LIKE 'https://%tse.jus.br/%'",
        )
        == 0
    )


def test_servico_views_for_the_person_page_keep_every_row_of_their_facts(
    full: tuple[Connection, Settings],
) -> None:
    con, _ = full
    assert scalar(con, "SELECT count(*) FROM servico.pessoas") == scalar(
        con, "SELECT count(*) FROM core.pessoas"
    )
    assert scalar(con, "SELECT count(*) FROM servico.pessoa_votos") == scalar(
        con, "SELECT count(*) FROM fatos.votos"
    )
    assert scalar(con, "SELECT count(*) FROM servico.pessoa_partidos") == scalar(
        con, "SELECT count(*) FROM fatos.pessoas_partidos"
    )
    ana = con.execute(
        "SELECT nome, profissoes, foto_url FROM servico.pessoas WHERE nome = 'Ana Árvore'"
    ).fetchone()
    assert ana is not None and ana[0] == "Ana Árvore" and ana[1]  # o cadastro da Câmara chega à ficha
