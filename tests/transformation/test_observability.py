"""Observabilidade: a fotografia de cada execução e os achados da comparação com a anterior."""

from plataforma_dados.core.warehouse import Connection, rows, scalar
from plataforma_dados.transformation import observability


def snap(
    con: Connection, run_id: int, table_rows: dict[str, int], nulls: float = 0.0, distinct: int = 100
) -> None:
    for table, n in table_rows.items():
        con.execute("INSERT INTO metadata.table_profile VALUES (?, 'marts', ?, ?)", (run_id, table, n))
        con.execute(
            "INSERT INTO metadata.column_profile VALUES (?, 'marts', ?, 'id', 'BIGINT', ?, ?)",
            (run_id, table, nulls, distinct),
        )


def found(con: Connection, run_id: int) -> set[tuple[str, str, str | None]]:
    return {
        (r["status"], r["check_name"], r["table_name"])
        for r in rows(
            con, "SELECT status, check_name, table_name FROM metadata.data_checks WHERE run_id = ?", (run_id,)
        )
    }


def test_the_first_snapshot_has_nothing_to_compare_and_says_so(con: Connection) -> None:
    snap(con, 1, {"votos": 1000})
    assert observability.compare(con, 1) == 0
    assert found(con, 1) == {("ok", "primeira_fotografia", None)}


def test_a_stable_run_has_no_findings(con: Connection) -> None:
    snap(con, 1, {"votos": 1000})
    snap(con, 2, {"votos": 1010})
    assert observability.compare(con, 2) == 0


def test_volume_that_collapses_or_explodes_is_reported_with_the_right_severity(con: Connection) -> None:
    snap(con, 1, {"a": 1000, "b": 1000, "c": 1000, "pequena": 10})
    snap(con, 2, {"a": 700, "b": 400, "c": 2500, "pequena": 1})
    assert observability.compare(con, 2) == 3
    assert found(con, 2) == {
        ("warn", "volume_caiu", "a"),
        ("error", "volume_caiu", "b"),
        ("warn", "volume_explodiu", "c"),
    }


def test_a_table_that_disappears_is_an_error_and_a_new_one_is_information(con: Connection) -> None:
    snap(con, 1, {"velha": 500})
    snap(con, 2, {"nova": 500})
    assert observability.compare(con, 2) == 1
    assert found(con, 2) == {("error", "tabela_sumiu", "velha"), ("ok", "tabela_nova", "nova")}


def test_nulls_that_grow_in_a_mart_column_and_distinct_values_that_collapse_are_reported(
    con: Connection,
) -> None:
    snap(con, 1, {"votos": 1000}, nulls=0.01, distinct=1000)
    snap(con, 2, {"votos": 1000}, nulls=0.45, distinct=300)
    observability.compare(con, 2)
    assert found(con, 2) == {
        ("error", "nulos_aumentaram", "votos"),
        ("warn", "valores_distintos_cairam", "votos"),
    }


def test_a_column_removed_from_a_mart_is_an_error_and_a_new_one_is_information(con: Connection) -> None:
    snap(con, 1, {"votos": 1000})
    snap(con, 2, {"votos": 1000})
    con.execute("DELETE FROM metadata.column_profile WHERE run_id = 2")
    con.execute("INSERT INTO metadata.column_profile VALUES (2, 'marts', 'votos', 'novo', 'BIGINT', 0.0, 5)")
    observability.compare(con, 2)
    assert found(con, 2) == {("error", "coluna_removida", "votos"), ("ok", "coluna_nova", "votos")}


def test_profile_counts_rows_everywhere_and_profiles_columns_only_in_the_marts(con: Connection) -> None:
    con.execute("CREATE SCHEMA marts")
    con.execute("CREATE TABLE marts.t (id BIGINT, nome VARCHAR)")
    con.execute("INSERT INTO marts.t VALUES (1, 'a'), (2, NULL), (3, NULL), (4, 'd')")
    con.execute("CREATE SCHEMA staging")
    con.execute("CREATE TABLE staging.s (x INTEGER)")
    assert observability.profile(con, 9) == 5  # as 3 tabelas de identity e as 2 criadas aqui
    assert (
        scalar(con, "SELECT row_count FROM metadata.table_profile WHERE run_id = 9 AND table_name = 't'") == 4
    )
    nulls = scalar(
        con, "SELECT null_rate FROM metadata.column_profile WHERE run_id = 9 AND column_name = 'nome'"
    )
    assert nulls == 0.5
    assert (
        scalar(con, "SELECT null_rate FROM metadata.column_profile WHERE run_id = 9 AND table_name = 's'")
        is None
    )
    assert "metadata" not in {
        r[0] for r in con.execute("SELECT schema_name FROM metadata.table_profile").fetchall()
    }


def test_the_report_says_what_changed_and_fails_only_when_there_is_an_error(con: Connection) -> None:
    snap(con, 1, {"votos": 1000})
    snap(con, 2, {"votos": 400})
    con.execute(
        "INSERT INTO metadata.runs (id, stage, started_at, status) VALUES (2, 'transform_post', '2026-10-24', 'ok')"
    )
    observability.compare(con, 2)
    lines, failed = observability.report(con)
    assert failed and any("volume_caiu" in line and "de 1000 para 400" in line for line in lines)
    clean = observability.report(con)[0]
    assert clean[0].startswith("Execução 2")
