"""`replace_view`: refazer a view do raw não pode perder as descrições (o DuckDB as perde)."""

import duckdb

from dado_publico_brasil.core.warehouse import replace_view, scalar


def test_replacing_a_view_keeps_the_descriptions_of_the_view_and_of_the_columns_that_remain() -> None:
    con = duckdb.connect()
    con.execute("CREATE SCHEMA s")
    con.execute("CREATE VIEW s.v AS SELECT 1 AS a, 2 AS b")
    con.execute("COMMENT ON VIEW s.v IS 'a view d''água'")
    con.execute("COMMENT ON COLUMN s.v.a IS 'coluna a'")
    con.execute("COMMENT ON COLUMN s.v.b IS 'coluna b'")
    replace_view(con, "s", "v", "SELECT 1 AS a, 3 AS c")
    assert scalar(con, "SELECT comment FROM duckdb_views() WHERE view_name = 'v'") == "a view d'água"
    found = dict(
        con.execute("SELECT column_name, comment FROM duckdb_columns() WHERE table_name = 'v'").fetchall()
    )
    assert found == {"a": "coluna a", "c": None}  # a que saiu perde a descrição; a nova ainda não tem
