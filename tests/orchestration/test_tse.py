"""TSE e ligação entre fontes: candidaturas ao Congresso, regra de nome civil e nascimento únicos, fusão e privacidade."""

from dado_publico_brasil.core.settings import Settings
from dado_publico_brasil.core.warehouse import Connection, columns, rows, scalar

Env = tuple[Connection, Settings]


def test_raw_has_candidacies_of_every_office_from_the_brasil_file_and_never_the_personal_documents(
    full: Env,
) -> None:
    con, _ = full
    cols = set(columns(con, "raw_federal_tse", "candidaturas"))
    assert not {"nr_cpf_candidato", "ds_email", "nr_titulo_eleitoral_candidato", "nm_social_candidato"} & cols
    found = {r["sq_candidato"] for r in rows(con, "SELECT sq_candidato FROM raw_federal_tse.candidaturas")}
    # 1006 é deputado estadual e 1010 a 1014 são municipais: entram no raw (todos os cargos); 9999 só existe no
    # arquivo do estado (só o _BRASIL.csv é lido)
    assert found == {"1001", "1002", "1003", "1004", "1005", "1006", "1010", "1011", "1012", "1013", "1014"}
    leaked = scalar(con, "SELECT COUNT(*) FROM raw_federal_tse.candidaturas WHERE nm_candidato LIKE '%@%'")
    assert leaked == 0


def test_candidacy_is_linked_to_the_person_by_civil_name_and_birth_date(full: Env) -> None:
    con, _ = full
    found = con.execute(
        "SELECT p.nome, c.ano_eleicao, c.cargo, c.partido, c.situacao_candidatura, c.resultado, c.uf "
        "FROM marts.candidaturas c JOIN marts.pessoas p USING (id_pessoa) ORDER BY c.id_candidatura"
    ).fetchall()
    assert found == [
        ("Bia", 2022, "Deputado federal", "BBB", "Deferido", "Eleito por qp", "RJ"),
        ("Ana Árvore", 2022, "Deputado federal", "AAA", "Deferido", "Não eleito", "SP"),
    ]


def test_homonyms_in_the_same_election_and_unmatched_candidates_are_not_linked_and_are_measured(
    full: Env,
) -> None:
    con, _ = full
    linked = {r["id_candidatura"] for r in rows(con, "SELECT id_candidatura FROM marts.candidaturas")}
    assert linked == {
        "2022:RJ:1001",
        "2022:SP:1002",
    }  # 1003 e 1004 (mesmo nome e nascimento) e 1005 (sem pessoa) ficam de fora
    gap = scalar(
        con, "SELECT failures FROM metadata.dbt_results WHERE unique_id LIKE '%eleitos_federais_sem_vinculo%'"
    )
    assert gap == 1  # Carlos, eleito sem correspondente


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
    assert scalar(con, "SELECT COUNT(*) FROM marts.pessoas") == scalar(
        con, "SELECT COUNT(*) FROM identity.pessoa"
    )


def test_senator_detail_gives_birth_naturality_and_photo_but_not_email_or_address(full: Env) -> None:
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
    cols = set(columns(con, "raw_federal_senado", "senadores_detalhe"))
    assert not {c for c in cols if "email" in c or "endereco" in c}


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
