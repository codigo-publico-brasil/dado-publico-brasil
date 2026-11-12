"""Pessoas de todo eleito do TSE (ADR 0031): criação, estabilidade, fusão e os casos que não podem fundir."""

from pathlib import Path

import pytest

from dado_publico_brasil.core import migrations
from dado_publico_brasil.core.settings import Settings
from dado_publico_brasil.core.warehouse import Connection, scalar
from dado_publico_brasil.transformation import identity

NOW = "2026-10-27T00:00:00"
ELECTED_TYPE = "candidatura_de_eleito"


@pytest.fixture
def con(tmp_path: Path) -> Connection:
    con = migrations.open_warehouse(Settings(storage_root=tmp_path))
    con.execute("CREATE SCHEMA IF NOT EXISTS intermediate")
    con.execute(
        "CREATE OR REPLACE TABLE intermediate.int_pessoas_grupos (fonte VARCHAR, id_tipo VARCHAR, "
        "id_na_fonte VARCHAR, grupo VARCHAR, metodo VARCHAR, metodo_fusao VARCHAR)"
    )
    con.execute(
        "CREATE OR REPLACE TABLE intermediate.fontes_identidade "
        "(fonte VARCHAR, precedencia INTEGER, fl_vinculo_derivado BOOLEAN)"
    )
    con.execute(
        "INSERT INTO intermediate.fontes_identidade VALUES ('camara', 1, false), ('senado', 1, false), ('tse', 2, true)"
    )
    con.execute(
        "CREATE OR REPLACE TABLE intermediate.int_vinculos_propostos (origem_fonte VARCHAR, origem_tipo VARCHAR, "
        "id_origem VARCHAR, destino_fonte VARCHAR, destino_tipo VARCHAR, id_destino VARCHAR, metodo VARCHAR)"
    )
    return con


def groups(con: Connection, *rows: tuple[str, str], source: str = "tse", id_type: str = ELECTED_TYPE) -> None:
    con.execute("DELETE FROM intermediate.int_pessoas_grupos")
    for candidacy, group in rows:
        con.execute(
            "INSERT INTO intermediate.int_pessoas_grupos VALUES (?, ?, ?, ?, 'metodo do grupo', 'fusao do grupo')",
            (source, id_type, candidacy, group),
        )


def official(con: Connection, source: str, id_type: str, source_id: str) -> int:
    """Uma pessoa oficial (Câmara ou Senado), como a identidade as cria."""
    person = int(scalar(con, "SELECT nextval('identity.seq_pessoas')"))
    con.execute("INSERT INTO identity.pessoas VALUES (?, ?)", (person, NOW))
    con.execute(
        "INSERT INTO identity.pessoas_identificadores VALUES (?, ?, ?, ?, 'teste', 'teste', ?)",
        (source, id_type, source_id, person, NOW),
    )
    return person


def person_of(con: Connection, candidacy: str, source: str = "tse") -> int | None:
    found = con.execute(
        "SELECT id_pessoa FROM identity.pessoas_identificadores WHERE fonte = ? AND id_tipo = ? AND id_na_fonte = ?",
        (source, ELECTED_TYPE, candidacy),
    ).fetchall()
    assert len(found) <= 1
    return int(found[0][0]) if found else None


def test_each_group_becomes_one_person_and_all_its_candidacies_join_it(con: Connection) -> None:
    groups(con, ("2016:1", "g1"), ("2020:1", "g1"), ("2020:2", "g2"))
    assert identity._people_of_groups(con, NOW) == 2
    assert person_of(con, "2016:1") == person_of(con, "2020:1") != person_of(con, "2020:2")
    assert scalar(con, "SELECT COUNT(*) FROM identity.pessoas") == 2


def test_running_again_changes_nothing(con: Connection) -> None:
    groups(con, ("2016:1", "g1"), ("2020:1", "g1"), ("2020:2", "g2"))
    identity._people_of_groups(con, NOW)
    before = con.execute("SELECT * FROM identity.pessoas_identificadores ORDER BY id_na_fonte").fetchall()
    assert identity._people_of_groups(con, NOW) == 0
    assert (
        con.execute("SELECT * FROM identity.pessoas_identificadores ORDER BY id_na_fonte").fetchall()
        == before
    )


def test_the_group_label_may_change_without_creating_another_person(con: Connection) -> None:
    """O rótulo do grupo não é estável (id_pessoa_tse): a âncora é a candidatura."""
    groups(con, ("2016:1", "rotulo-antigo"))
    identity._people_of_groups(con, NOW)
    person = person_of(con, "2016:1")
    groups(con, ("2016:1", "rotulo-novo"), ("2020:1", "rotulo-novo"))
    assert identity._people_of_groups(con, NOW) == 0
    assert person_of(con, "2016:1") == person_of(con, "2020:1") == person


def test_a_later_election_joins_the_existing_person(con: Connection) -> None:
    groups(con, ("2016:1", "g1"))
    identity._people_of_groups(con, NOW)
    person = person_of(con, "2016:1")
    groups(con, ("2016:1", "g1"), ("2024:1", "g1"))
    assert identity._people_of_groups(con, NOW) == 0
    assert person_of(con, "2024:1") == person


def test_a_tse_only_person_is_absorbed_by_the_official_person_who_appears_later(con: Connection) -> None:
    groups(con, ("2022:1", "g1"))
    identity._people_of_groups(con, NOW)
    tse_only = person_of(con, "2022:1")
    deputy = official(con, "camara", "deputado", "99")  # chave mais nova que a pessoa do TSE
    assert deputy is not None and tse_only is not None and deputy > tse_only
    con.execute(
        "INSERT INTO intermediate.int_vinculos_propostos VALUES ('tse', 'candidato', '2022:1', 'camara', 'deputado', "
        "'99', 'teste')"
    )
    identity._people_of_groups(con, NOW)
    assert person_of(con, "2022:1") == deputy  # a oficial sobrevive, mesmo sendo a mais nova
    assert scalar(con, "SELECT COUNT(*) FROM identity.pessoas WHERE id_pessoa = ?", (tse_only,)) == 0
    assert con.execute(
        "SELECT id_pessoa_absorvida, id_pessoa_sobrevivente FROM identity.pessoas_fusoes"
    ).fetchall() == [(tse_only, deputy)]


def test_a_group_touching_two_official_people_is_never_merged(con: Connection) -> None:
    groups(con, ("2018:1", "g1"), ("2022:1", "g1"))
    senator = official(con, "senado", "senador", "5")
    deputy = official(con, "camara", "deputado", "9")
    for candidacy, source, id_type, source_id in (
        ("2018:1", "senado", "senador", "5"),
        ("2022:1", "camara", "deputado", "9"),
    ):
        con.execute(
            "INSERT INTO intermediate.int_vinculos_propostos VALUES ('tse', 'candidato', ?, ?, ?, ?, 'teste')",
            (candidacy, source, id_type, source_id),
        )
    identity._people_of_groups(con, NOW)
    assert scalar(con, "SELECT COUNT(*) FROM identity.pessoas_fusoes") == 0
    assert {senator, deputy} <= {
        int(r[0]) for r in con.execute("SELECT id_pessoa FROM identity.pessoas").fetchall()
    }
    assert (
        person_of(con, "2018:1") is None and person_of(con, "2022:1") is None
    )  # fica de fora, o teste de lacuna mede


def test_components_join_people_that_share_a_group() -> None:
    pairs = [("g1", 1), ("g1", 2), ("g2", 2), ("g2", 3), ("g3", 7), ("g4", 8), ("g4", 9)]
    assert sorted(sorted(c) for c in identity._components(pairs)) == [[1, 2, 3], [8, 9]]


def test_the_method_of_the_group_and_of_the_merge_come_from_the_groups_model(con: Connection) -> None:
    groups(con, ("2022:1", "g1"))
    identity._people_of_groups(con, NOW)
    assert con.execute("SELECT metodo FROM identity.pessoas_identificadores").fetchall() == [
        ("metodo do grupo",)
    ]
    deputy = official(con, "camara", "deputado", "99")
    con.execute(
        "INSERT INTO intermediate.int_vinculos_propostos VALUES ('tse', 'candidato', '2022:1', 'camara', 'deputado', "
        "'99', 'teste')"
    )
    identity._people_of_groups(con, NOW)
    assert person_of(con, "2022:1") == deputy
    assert con.execute("SELECT metodo FROM identity.pessoas_fusoes").fetchall() == [("fusao do grupo",)]


def test_a_new_source_enters_by_the_seed_alone(con: Connection) -> None:
    """Fonte de cadastro (precedência 1) e fonte derivada declaradas na seed: nada de nome de fonte no código."""
    con.execute("DELETE FROM intermediate.fontes_identidade")
    con.execute(
        "INSERT INTO intermediate.fontes_identidade VALUES ('cadastro_x', 1, false), ('derivada_y', 2, true)"
    )
    groups(con, ("a:1", "g1"), source="derivada_y")
    identity._people_of_groups(con, NOW)
    derived_only = person_of(con, "a:1", "derivada_y")
    official_person = official(con, "cadastro_x", "membro", "7")
    assert official_person > derived_only  # type: ignore[operator]
    con.execute(
        "INSERT INTO intermediate.int_vinculos_propostos VALUES ('derivada_y', 'candidato', 'a:1', 'cadastro_x', "
        "'membro', '7', 'teste')"
    )
    identity._people_of_groups(con, NOW)
    assert person_of(con, "a:1", "derivada_y") == official_person  # o cadastro sobrevive
