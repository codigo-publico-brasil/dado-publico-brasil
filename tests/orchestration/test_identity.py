"""Identidade de pessoas: chave própria, ponte de identificadores e estabilidade da chave."""

from plataforma_dados.core import warehouse
from plataforma_dados.core.settings import Settings
from plataforma_dados.core.warehouse import Connection, scalar
from plataforma_dados.transformation import build, identity


def bridge(con: Connection) -> list[tuple[object, ...]]:
    return con.execute(
        "SELECT source, id_type, source_id, method FROM identity.pessoa_identificador ORDER BY source_id"
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
    ]
    assert all(method for *_, method in found)
    assert scalar(con, "SELECT COUNT(DISTINCT id_pessoa) FROM identity.pessoa_identificador") == 3


def test_person_keys_do_not_change_when_the_pipeline_runs_again(
    full: tuple[Connection, Settings],
) -> None:
    con, settings = full
    before = con.execute(
        "SELECT source_id, id_pessoa FROM identity.pessoa_identificador ORDER BY 1"
    ).fetchall()
    con.close()
    build.transform(settings, "transform_pre", *build.PRE_IDENTITY)
    con = warehouse.connect(settings)
    assert identity.resolve(con) == (3, 0)  # 3 vistos, nenhuma pessoa nova
    after = con.execute(
        "SELECT source_id, id_pessoa FROM identity.pessoa_identificador ORDER BY 1"
    ).fetchall()
    assert before == after
    assert scalar(con, "SELECT COUNT(*) FROM identity.pessoa") == 3


def test_a_deputy_seen_only_in_the_votes_also_becomes_a_person(
    full: tuple[Connection, Settings],
) -> None:
    con, _ = full
    assert con.execute(
        "SELECT p.nome, p.data_nascimento, p.foto_url FROM marts.pessoas p "
        "JOIN identity.pessoa_identificador i USING (id_pessoa) WHERE i.source_id = '12'"
    ).fetchone() == ("Caio", None, None)
