"""Marts (entidades prontas para consumo) e o que as camadas anteriores entregam a eles."""

from dado_publico_brasil.core.settings import Settings
from dado_publico_brasil.core.warehouse import Connection, scalar, tables
from dado_publico_brasil.transformation import catalog


def person_id(con: Connection, name: str) -> int:
    return int(scalar(con, "SELECT id_pessoa FROM marts.dim_pessoas_cadastro WHERE nome = ?", (name,)))


def test_person_has_counts_last_party_search_keys_and_standardized_names(
    full: tuple[Connection, Settings],
) -> None:
    con, _ = full
    row = con.execute(
        "SELECT nome, nome_civil, nome_ordem, nome_busca, qtd_propostas, qtd_votos, ultimo_partido, "
        "ultima_uf, profissoes, primeira_legislatura_com_voto, foto_url, dt_nascimento, "
        "dt_captura IS NOT NULL FROM marts.dim_pessoas_cadastro WHERE nome = 'Ana Árvore'"
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
        "SELECT sigla, ementa, ementa_oficial, situacao, fonte_url FROM marts.fct_proposicoes "
        "WHERE id_proposicao = '102'"
    ).fetchone() == (
        "PL 9/2019",
        "Requer o desarquivamento de proposições.",
        "REQUER O DESARQUIVAMENTO DE PROPOSIÇÕES.",
        None,
        "https://www.camara.leg.br/proposicoesWeb/fichadetramitacao?idProposicao=102",
    )
    assert con.execute(
        "SELECT situacao, orgao_ultimo_status FROM marts.fct_proposicoes WHERE id_proposicao = '100'"
    ).fetchone() == ("Aguardando Parecer", "CCJC")


def test_authorship_counts_the_authors_and_leaves_out_authors_that_are_not_people(
    full: tuple[Connection, Settings],
) -> None:
    con, _ = full
    ana = person_id(con, "Ana Árvore")
    rows = con.execute(
        "SELECT id_proposicao, ordem_assinatura, qtd_autores, proponente FROM marts.brg_proposicoes_autorias "
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
        "SELECT COUNT(*) FROM marts.brg_proposicoes_autorias WHERE id_proposicao = '100' AND id_pessoa IS NULL AND nome_autor = 'Senado Federal'"
    ).fetchone()
    assert kept == (1,)  # o autor que não é pessoa fica no mart, sem id_pessoa


def test_voting_lists_the_propositions_and_the_official_result(
    full: tuple[Connection, Settings],
) -> None:
    con, _ = full
    assert con.execute(
        "SELECT descricao, aprovada, votos_sim, votos_nao, proposicoes FROM marts.fct_votacoes "
        "WHERE id_votacao = '100-1'"
    ).fetchone() == ("Aprovada a PEC.", 1, 2, 1, "PEC 5/2024")


def test_votes_carry_the_party_and_state_of_the_day(full: tuple[Connection, Settings]) -> None:
    con, _ = full
    ana = person_id(con, "Ana Árvore")
    assert con.execute(
        "SELECT voto, partido_na_fonte, uf FROM marts.fct_votos WHERE id_pessoa = ? ORDER BY dt_voto DESC",
        (ana,),
    ).fetchall() == [("Não", "BBB", "SP"), ("Sim", "AAA", "SP")]


def test_staging_does_not_join_and_keeps_one_row_per_raw_row(
    full: tuple[Connection, Settings],
) -> None:
    con, _ = full
    assert scalar(con, "SELECT COUNT(*) FROM staging.stg_camara__votos") == scalar(
        con, "SELECT COUNT(*) FROM raw_federal_camara.votacoes_votos"
    )


def test_every_table_of_the_marts_is_declared_and_named_by_its_type(
    full: tuple[Connection, Settings],
) -> None:
    con, settings = full
    declared = {t["name"] for t in catalog.tables(settings) if t["schema"] == "marts"}
    found = tables(con, "marts")
    assert declared <= set(found)  # as sementes (dim_cargos...) estão no warehouse e descritas no YAML delas
    assert all(name.startswith(("dim_", "fct_", "brg_", "agg_", "app_")) for name in found)


def test_descriptions_are_persisted_in_the_warehouse_for_tables_and_columns(
    full: tuple[Connection, Settings],
) -> None:
    con, _ = full
    table = scalar(
        con, "SELECT comment FROM duckdb_tables() WHERE schema_name='marts' AND table_name='fct_votos'"
    )
    column = scalar(
        con,
        "SELECT comment FROM duckdb_columns() "
        "WHERE schema_name='marts' AND table_name='fct_votos' AND column_name='id_votacao'",
    )
    assert table
    assert column


def test_organs_and_fronts_link_members_to_people_and_report_unknown_deputies(
    full: tuple[Connection, Settings],
) -> None:
    con, _ = full
    assert scalar(con, "SELECT count(*) FROM marts.dim_orgaos") == 2
    members = con.execute(
        "SELECT p.nome, m.cargo, m.dt_fim FROM marts.brg_orgaos_membros m JOIN marts.dim_pessoas_cadastro p USING (id_pessoa) "
        "ORDER BY p.nome, m.dt_fim NULLS FIRST"
    ).fetchall()
    # as duas linhas distintas da fonte para a mesma pessoa e cargo são mantidas; o deputado 99 fica de fora
    assert [(r[0], r[1]) for r in members] == [("Ana Árvore", "Presidente")] * 2 + [("Bia", "Titular")]
    front = con.execute(
        "SELECT titulo, situacao, id_pessoa_coordenador IS NOT NULL FROM marts.dim_frentes"
    ).fetchall()
    assert front == [("Frente X", "Em andamento", True)]
    assert scalar(con, "SELECT count(*) FROM marts.brg_frentes_membros") == 2


def test_photo_comes_from_the_fronts_when_the_person_has_no_vote_photo(
    full: tuple[Connection, Settings],
) -> None:
    con, _ = full
    assert (
        scalar(con, "SELECT foto_url FROM marts.dim_pessoas_cadastro WHERE nome = 'Bia'")
        == "http://foto/11.jpg"
    )


def test_party_lineage_comes_from_the_curated_table_and_every_event_cites_the_official_page(
    full: tuple[Connection, Settings],
) -> None:
    con, _ = full
    changes = con.execute(
        "SELECT sigla_anterior, sigla_posterior, tipo, ano FROM marts.dim_partidos_linhagem "
        "WHERE tipo = 'mudança de nome'"
    ).fetchall()
    assert changes  # a tabela curada traz mudanças de nome...
    assert all(before != after and year for before, after, _, year in changes)  # ...cada uma com o ano
    assert (
        scalar(
            con,
            "SELECT COUNT(*) FROM marts.dim_partidos_linhagem WHERE fonte_url NOT LIKE 'https://%tse.jus.br/%'",
        )
        == 0
    )


def test_servico_views_for_the_person_page_keep_every_row_of_their_facts(
    full: tuple[Connection, Settings],
) -> None:
    con, _ = full
    assert scalar(con, "SELECT count(*) FROM marts.app_pessoas") == scalar(
        con, "SELECT count(*) FROM marts.dim_pessoas"
    )
    assert scalar(con, "SELECT count(*) FROM marts.app_pessoa_votos") == scalar(
        con, "SELECT count(*) FROM marts.fct_votos"
    )
    assert scalar(con, "SELECT count(*) FROM marts.app_pessoa_partidos") == scalar(
        con, "SELECT count(*) FROM marts.fct_pessoas_partidos"
    )
    ana = con.execute(
        "SELECT nome, profissoes, foto_url FROM marts.app_pessoas WHERE nome = 'Ana Árvore'"
    ).fetchone()
    assert ana is not None and ana[0] == "Ana Árvore" and ana[1]  # o cadastro da Câmara chega à ficha


def test_app_views_carry_the_source_and_capture_date_and_the_birth_state_from_the_tse(
    full: tuple[Connection, Settings],
) -> None:
    con, _ = full
    for view in ("app_cargo_ocupantes", "app_pessoa_campanhas", "app_pessoas"):
        total, with_source = con.execute(
            f"SELECT count(*), count(fonte_url) FILTER (WHERE dt_captura IS NOT NULL) FROM marts.{view}"
        ).fetchone()  # type: ignore[misc]
        assert total > 0 and with_source == total, view
    assert not scalar(
        con, "SELECT count(*) FROM marts.app_cargo_ocupantes WHERE ano_inicio IS NULL OR fonte_url IS NULL"
    )
    allowed = {"novato", "reeleito", "retorno", None}
    found = {
        r[0] for r in con.execute("SELECT DISTINCT tipo_mandato FROM marts.app_cargo_ocupantes").fetchall()
    }
    assert found <= allowed
    # a UF de nascimento da ficha vem do cadastro da Câmara ou do Senado e, sem ele, da candidatura do TSE
    assert (
        scalar(
            con,
            "SELECT count(*) FROM marts.app_pessoas a JOIN marts.fct_candidaturas c USING (id_pessoa) "
            "WHERE a.uf_nascimento IS NULL AND c.uf_nascimento IS NOT NULL",
        )
        == 0
    )
