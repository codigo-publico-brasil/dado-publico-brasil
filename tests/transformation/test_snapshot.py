"""Cópia imutável da identidade: grava, nunca sobrescreve e denuncia qualquer divergência."""

from dado_publico_brasil.core.settings import Settings
from dado_publico_brasil.core.warehouse import Connection, scalar
from dado_publico_brasil.transformation import snapshot


def add_person(con: Connection) -> None:
    con.execute("INSERT INTO identity.pessoa (created_at) VALUES ('2026-10-23')")


def test_without_a_snapshot_the_check_asks_for_one(con: Connection, settings: Settings) -> None:
    assert snapshot.problems(con, settings) == ["identidade sem snapshot: rode `dado-publico identity`"]


def test_snapshot_has_every_identity_table_and_matches_the_warehouse_right_after(
    con: Connection, settings: Settings
) -> None:
    add_person(con)
    folder = snapshot.take(con, settings)
    assert {f.name for f in folder.glob("*.parquet")} == {
        "pessoa.parquet",
        "pessoa_fusao.parquet",
        "pessoa_identificador.parquet",
    }
    assert snapshot.problems(con, settings) == []


def test_each_snapshot_is_a_new_folder_and_the_older_ones_stay_as_they_were(
    con: Connection, settings: Settings
) -> None:
    add_person(con)
    first = snapshot.take(con, settings)
    before = (first / "pessoa.parquet").read_bytes()
    add_person(con)
    second = snapshot.take(con, settings)
    assert first != second
    assert (first / "pessoa.parquet").read_bytes() == before
    assert scalar(con, f"SELECT count(*) FROM read_parquet('{(first / 'pessoa.parquet').as_posix()}')") == 1


def test_a_change_in_the_warehouse_after_the_snapshot_is_reported(
    con: Connection, settings: Settings
) -> None:
    add_person(con)
    snapshot.take(con, settings)
    add_person(con)
    found = snapshot.problems(con, settings)
    assert len(found) == 1 and "pessoa difere do warehouse em 1 linhas" in found[0]
