"""Identidade de pessoas: chave própria, ponte de identificadores e estabilidade da chave."""

from dado_publico_brasil.core import warehouse
from dado_publico_brasil.core.settings import Settings
from dado_publico_brasil.core.warehouse import Connection, scalar
from dado_publico_brasil.transformation import build, identity


def bridge(con: Connection) -> list[tuple[object, ...]]:
    return con.execute(
        "SELECT fonte, id_tipo, id_na_fonte, metodo FROM identity.pessoas_identificadores "
        f"WHERE id_tipo <> '{identity.ELECTED_TYPE}' ORDER BY id_na_fonte"
    ).fetchall()


def test_each_deputy_gets_a_person_with_its_own_key_and_a_traceable_method(
    full: tuple[Connection, Settings],
) -> None:
    con, _ = full
    found = bridge(con)
    assert [(s, t, i) for s, t, i, _ in found] == [
        ("camara", "deputado", "10"),
        ("camara", "deputado", "11"),
        ("camara", "deputado", "12"),
        ("tse", "candidato", "2018:SP:2007"),  # Ana mudou de nome civil: ligada pelo nome de urna
        ("tse", "candidato", "2022:RJ:1001"),
        ("tse", "candidato", "2022:SP:1002"),
        ("senado", "senador", "5000"),
        ("senado", "senador", "5001"),
        ("senado", "senador", "5002"),
        ("senado", "senador", "5003"),
    ]
    assert all(method for *_, method in found)
    assert (
        scalar(
            con,
            "SELECT COUNT(DISTINCT id_pessoa) FROM identity.pessoas_identificadores "
            f"WHERE id_tipo <> '{identity.ELECTED_TYPE}'",
        )
        == 6
    )


def test_person_keys_do_not_change_when_the_pipeline_runs_again(
    full: tuple[Connection, Settings],
) -> None:
    con, settings = full
    people_before = scalar(con, "SELECT COUNT(*) FROM identity.pessoas")
    before = con.execute(
        "SELECT id_na_fonte, id_pessoa FROM identity.pessoas_identificadores ORDER BY 1"
    ).fetchall()
    con.close()
    build.transform(settings, "transform_pre", *build.PRE_IDENTITY)
    con = warehouse.connect(settings)
    assert identity.resolve(con) == (7, 0)  # 7 vistos, nenhuma pessoa nova e nenhuma fusão a repetir
    after = con.execute(
        "SELECT id_na_fonte, id_pessoa FROM identity.pessoas_identificadores ORDER BY 1"
    ).fetchall()
    assert before == after
    assert scalar(con, "SELECT COUNT(*) FROM identity.pessoas") == people_before


def test_a_deputy_seen_only_in_the_votes_also_becomes_a_person(
    full: tuple[Connection, Settings],
) -> None:
    con, _ = full
    assert con.execute(
        "SELECT p.nome, p.dt_nascimento, p.foto_url FROM marts.dim_pessoas_cadastro p "
        "JOIN identity.pessoas_identificadores i USING (id_pessoa) WHERE i.id_na_fonte = '12'"
    ).fetchone() == ("Caio", None, None)


def test_people_of_different_sources_with_the_same_name_are_never_linked(
    full: tuple[Connection, Settings],
) -> None:
    con, _ = full
    found = con.execute(
        "SELECT fonte, id_pessoa FROM marts.dim_pessoas_cadastro WHERE nome = 'Ana Árvore' ORDER BY fonte"
    ).fetchall()
    assert [f for f, _ in found] == ["camara", "senado"]
    assert found[0][1] != found[1][1]


def test_every_elected_candidacy_has_a_person_and_those_who_never_won_have_none(
    full: tuple[Connection, Settings],
) -> None:
    con, _ = full
    elected = scalar(
        con,
        "SELECT COUNT(DISTINCT id_candidatura) FROM staging.stg_tse__candidaturas WHERE resultado LIKE 'Eleito%'",
    )
    assert elected > 0
    without_person = scalar(
        con,
        "SELECT COUNT(*) FROM marts.fct_mandatos WHERE id_pessoa IS NULL",
    )
    assert without_person == 0
    never_elected = con.execute(
        "SELECT COUNT(*) FROM staging.stg_tse__candidaturas c WHERE nome_urna IN ('BETO', 'BETO B') "
        "AND id_candidatura IN (SELECT id_na_fonte FROM identity.pessoas_identificadores "
        f"WHERE id_tipo = '{identity.ELECTED_TYPE}')"
    ).fetchone()
    assert never_elected == (0,)


def test_an_elected_deputy_keeps_the_person_the_chamber_gave_them(full: tuple[Connection, Settings]) -> None:
    con, _ = full
    deputy = scalar(
        con,
        "SELECT id_pessoa FROM identity.pessoas_identificadores WHERE fonte = 'tse' AND id_tipo = 'candidato'"
        " AND id_na_fonte = '2022:RJ:1001'",
    )
    assert deputy == scalar(
        con,
        "SELECT id_pessoa FROM identity.pessoas_identificadores WHERE fonte = 'tse' "
        f"AND id_tipo = '{identity.ELECTED_TYPE}' AND id_na_fonte = '2022:RJ:1001'",
    )
    assert (
        scalar(
            con,
            "SELECT COUNT(*) FROM identity.pessoas_identificadores WHERE id_pessoa = ? AND fonte IN ('camara', 'senado')",
            (deputy,),
        )
        >= 1
    )  # a pessoa é a oficial, não uma nova do TSE


def test_core_people_have_the_source_of_each_attribute_and_only_published_data(
    full: tuple[Connection, Settings],
) -> None:
    con, _ = full
    assert warehouse.columns(con, "marts", "dim_pessoas") == [
        "id_pessoa",
        "nome_civil",
        "fonte_nome_civil",
        "nome_publico",
        "fonte_nome_publico",
        "dt_nascimento",
        "fonte_dt_nascimento",
        "genero",
        "fonte_genero",
        "dt_entrada",
    ]
    assert scalar(con, "SELECT COUNT(*) FROM marts.dim_pessoas") == scalar(
        con, "SELECT COUNT(*) FROM identity.pessoas"
    )
    # o prefeito eleito só existe no TSE: tudo vem de lá, e o gênero só aparece quando a fonte diz masculino ou feminino
    assert con.execute(
        "SELECT fonte_nome_civil, fonte_dt_nascimento, genero FROM marts.dim_pessoas p "
        "JOIN identity.pessoas_identificadores i USING (id_pessoa) WHERE i.id_na_fonte LIKE '%:1010'"
    ).fetchone() == ("tse", "tse", "masculino")
