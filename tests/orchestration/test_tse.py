"""TSE e ligação entre fontes: candidaturas ao Congresso, regra de nome civil e nascimento únicos, fusão e privacidade."""

from dado_publico_brasil.core.settings import Settings
from dado_publico_brasil.core.warehouse import Connection, columns, rows, scalar

Env = tuple[Connection, Settings]


def test_raw_has_candidacies_of_every_office_from_the_brasil_file_and_never_the_personal_documents(
    full: Env,
) -> None:
    con, _ = full
    cols = set(columns(con, "raw_federal_tse", "candidaturas"))
    assert not {"nr_cpf_candidato", "ds_email", "nr_titulo_eleitoral_candidato"} & cols
    assert {
        "nm_social_candidato",
        "ds_estado_civil",
        "ds_ocupacao",
    } <= cols  # ADR 0029: o que o candidato declara
    found = {r["sq_candidato"] for r in rows(con, "SELECT sq_candidato FROM raw_federal_tse.candidaturas")}
    # 1006 é deputado estadual, 1010 a 1016 são municipais e 2005 e 2006 são de 2018: entram no raw (todos os cargos); 9999 só existe no
    # arquivo do estado (só o _BRASIL.csv é lido)
    assert found == {
        "1001",
        "1002",
        "1003",
        "1004",
        "1005",
        "1006",
        "1010",
        "1011",
        "1012",
        "1013",
        "1014",
        "1015",
        "1016",
        "2005",
        "2006",
        "2007",
        "2008",
        "2010",
        "3001",
    }
    leaked = scalar(con, "SELECT COUNT(*) FROM raw_federal_tse.candidaturas WHERE nm_candidato LIKE '%@%'")
    assert leaked == 0


def test_candidacy_is_linked_to_the_person_by_civil_name_and_birth_date(full: Env) -> None:
    con, _ = full
    found = con.execute(
        "SELECT p.nome, c.ano_eleicao, c.cargo, c.partido, c.situacao_candidatura, c.resultado, c.uf "
        "FROM marts.candidaturas c JOIN marts.pessoas p USING (id_pessoa) ORDER BY c.id_candidatura"
    ).fetchall()
    assert found == [
        (
            "Ana Árvore",
            2018,
            "Deputado federal",
            "AAA",
            "Deferido",
            "Não eleito",
            "SP",
        ),  # ligada pelo nome de urna
        ("Bia", 2022, "Deputado federal", "BBB", "Deferido", "Eleito por qp", "RJ"),
        ("Ana Árvore", 2022, "Deputado federal", "AAA", "Deferido", "Não eleito", "SP"),
    ]


def test_homonyms_in_the_same_election_and_unmatched_candidates_are_not_linked_and_are_measured(
    full: Env,
) -> None:
    con, _ = full
    linked = {r["id_candidatura"] for r in rows(con, "SELECT id_candidatura FROM marts.candidaturas")}
    assert linked == {
        "2018:SP:2007",  # ligada pelo nome de urna (mudou de nome civil)
        "2022:RJ:1001",
        "2022:SP:1002",
    }  # 1003 e 1004 (mesmo nome e nascimento) e 1005 (sem pessoa) ficam de fora
    gap = scalar(
        con, "SELECT failures FROM metadata.dbt_results WHERE unique_id LIKE '%eleitos_federais_sem_vinculo%'"
    )
    assert gap == 2  # Carlos, eleito sem correspondente em 2018 e em 2022


def test_deputy_and_senator_with_the_same_civil_name_and_birth_date_become_one_person(full: Env) -> None:
    con, _ = full
    ids = {
        r["id_na_fonte"]: r["id_pessoa"]
        for r in rows(
            con,
            "SELECT i.source_id AS id_na_fonte, i.id_pessoa FROM identity.pessoa_identificador i "
            "WHERE (i.source, i.source_id) IN (('camara', '11'), ('senado', '5003'))",
        )
    }
    assert len(set(ids.values())) == 1  # a chave mais antiga ficou
    fusao = rows(con, "SELECT * FROM marts.pessoas_fusoes")
    assert len(fusao) == 1 and fusao[0]["id_pessoa_sobrevivente"] == ids["11"]
    assert fusao[0]["id_pessoa_absorvida"] > fusao[0]["id_pessoa_sobrevivente"]
    assert "iguais e únicos" in fusao[0]["metodo"]
    assert (
        scalar(
            con, f"SELECT COUNT(*) FROM identity.pessoa WHERE id_pessoa = {fusao[0]['id_pessoa_absorvida']}"
        )
        == 0
    )


def test_the_merged_person_has_one_row_with_both_sources_and_the_chamber_data(full: Env) -> None:
    con, _ = full
    found = con.execute("SELECT fonte, fontes, nome FROM marts.pessoas WHERE nome = 'Bia'").fetchall()
    assert found == [("camara", "camara, senado", "Bia")]
    # marts.pessoas só tem parlamentares; as pessoas só do TSE (todo eleito, ADR 0031) estão em core.pessoas
    assert scalar(con, "SELECT COUNT(*) FROM marts.pessoas") == scalar(
        con,
        "SELECT COUNT(DISTINCT id_pessoa) FROM identity.pessoa_identificador WHERE source IN ('camara', 'senado')",
    )


def test_senator_detail_gives_birth_naturality_photo_and_the_institutional_contact(full: Env) -> None:
    con, _ = full
    row = con.execute(
        "SELECT dt_nascimento, municipio_nascimento, uf_nascimento, foto_url FROM marts.pessoas "
        "WHERE fonte = 'senado' AND nome = 'Beto Barreiras'"
    ).fetchone()
    assert (
        row is not None
        and str(row[0]) == "1970-05-05"
        and row[1:] == ("Santos", "SP", "http://foto/s5000.jpg")
    )
    contact = con.execute(
        "SELECT email_institucional, telefone_institucional, gabinete_endereco, pagina_url FROM marts.pessoas "
        "WHERE fonte = 'senado' AND nome = 'Beto Barreiras'"
    ).fetchone()
    assert contact == (
        "sen.exemplo@senado.leg.br",
        "33036777; 33036568",
        "Anexo 2, gabinete 5",
        "http://senado/perfil/5000",
    )


def test_the_tse_markers_for_no_value_never_reach_the_staging_tables(full: Env) -> None:
    con, _ = full
    assert (
        scalar(con, "SELECT COUNT(*) FROM raw_federal_tse.votacao WHERE nm_ue = '#NE'") > 0
    )  # o marcador chega ao raw
    tables = [
        name
        for (name,) in con.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'staging' AND table_name LIKE 'stg_tse__%'"
        ).fetchall()
    ]
    assert tables
    leaks = []
    for table in tables:
        for column in columns(con, "staging", table):
            count = scalar(
                con,
                f'SELECT COUNT(*) FROM staging."{table}" '
                f"WHERE upper(TRY_CAST(\"{column}\" AS VARCHAR)) IN ('#NE', '#NE#', '#NULO', '#NULO#')",
            )
            if count:
                leaks.append(f"{table}.{column}")
    assert leaks == []  # o raw espelha a fonte; da camada staging em diante o vazio é vazio


def test_candidate_declarations_reach_the_marts_and_documents_never_do(full: Env) -> None:
    con, _ = full
    row = con.execute(
        "SELECT nome_social, grau_instrucao, estado_civil, ocupacao, coligacao_nome, federacao_sigla "
        "FROM marts.candidaturas WHERE id_candidatura LIKE '2022:%:1001'"
    ).fetchone()
    assert row == ("Bia Social", "Superior completo", "Solteiro(a)", "Advogado", "COLIGACAO TESTE", "FED")
    all_columns = {c for t in ("candidaturas", "pessoas") for c in columns(con, "marts", t)}
    assert not {c for c in all_columns if "cpf" in c or "titulo" in c or "cor_raca" in c}


def test_linking_again_changes_nothing(full: Env) -> None:
    from dado_publico_brasil.transformation import identity

    con, _ = full
    before = scalar(con, "SELECT COUNT(*) FROM identity.pessoa_identificador")
    identity.resolve(con)
    assert scalar(con, "SELECT COUNT(*) FROM identity.pessoa_identificador") == before
    assert scalar(con, "SELECT COUNT(*) FROM identity.pessoa_fusao") == 1


def test_a_derived_tse_link_that_is_no_longer_proposed_is_removed_and_the_valid_ones_stay(full: Env) -> None:
    from dado_publico_brasil.transformation import identity

    con, _ = full
    valid = scalar(con, "SELECT COUNT(*) FROM identity.pessoa_identificador WHERE source = 'tse'")
    person = scalar(con, "SELECT min(id_pessoa) FROM identity.pessoa")
    con.execute(
        "INSERT INTO identity.pessoa_identificador VALUES ('tse', 'candidato', '2022:XX:777', ?, 'x', 'regra automática', 'x')",
        (person,),
    )  # a chave antiga, sem unidade eleitoral, que a carga corrigida não gera mais
    identity.resolve(con)
    assert scalar(con, "SELECT COUNT(*) FROM identity.pessoa_identificador WHERE source = 'tse'") == valid
    assert (
        scalar(con, "SELECT COUNT(*) FROM identity.pessoa_identificador WHERE source_id = '2022:XX:777'") == 0
    )


def test_a_renewed_election_with_another_code_does_not_enter_even_without_the_word_supplementary(
    full: Env,
) -> None:
    con, _ = full
    found = {r[0] for r in con.execute("SELECT sq_candidato FROM staging.stg_tse__candidaturas").fetchall()}
    assert 1010 in found  # a eleição ordinária entra
    assert 1014 not in found and 1016 not in found  # a suplementar e a renovada ficam só no raw
    assert scalar(con, "SELECT COUNT(*) FROM raw_federal_tse.candidaturas WHERE sq_candidato = '1016'") == 1
