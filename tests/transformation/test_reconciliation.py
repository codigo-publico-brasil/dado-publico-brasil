"""Teste dbt de reconciliação do raw (issue 156): o SQL real, renderizado sem o dbt, sobre um DuckDB sintético."""

from pathlib import Path
from types import SimpleNamespace

import duckdb
import jinja2
import yaml

from dado_publico_brasil.ingestion import contract as contracts

DBT = Path(__file__).resolve().parents[2] / "dbt"
SQL = (DBT / "tests/reconciliation/carga_do_raw_diferente_da_captura.sql").read_text(encoding="utf-8")


def render(con: duckdb.DuckDBPyConnection) -> str:
    """Renderiza o teste com um `graph` e um `adapter` mínimos: uma fonte `ano_a` com `escrita: replace_partition`."""
    table = SimpleNamespace(
        source_name="fonte_a",
        name="votos",
        meta={"escrita": "replace_partition"},
        database="memory",
        schema="raw_fonte_a",
        identifier="votos",
        relation_name="raw_fonte_a.votos",
    )
    ignored = SimpleNamespace(source_name="fonte_a", name="outro", meta={}, relation_name="raw_fonte_a.outro")
    env = jinja2.Environment(extensions=["jinja2.ext.do"])
    return env.from_string(SQL).render(
        execute=True,
        graph=SimpleNamespace(sources={"a": table, "b": ignored}),
        adapter=SimpleNamespace(get_relation=lambda *args: True),
        source=lambda schema, name: f"metadata.{name}",
    )


def warehouse(captures: dict[int, int], carregadas: int, raw: dict[int, int]) -> duckdb.DuckDBPyConnection:
    """`captures`: id da captura -> ano; `raw`: id da captura -> linhas no raw; a carga vigente é a da última."""
    con = duckdb.connect()
    con.execute("CREATE SCHEMA metadata; CREATE SCHEMA raw_fonte_a")
    con.execute("CREATE TABLE metadata.capturas (id_captura BIGINT, particao INTEGER)")
    con.execute(
        "CREATE TABLE metadata.fontes_verificacoes "
        "(id_verificacao BIGINT, fonte VARCHAR, dataset VARCHAR, particao INTEGER, verificacao VARCHAR, detalhe VARCHAR)"
    )
    con.execute("CREATE TABLE raw_fonte_a.votos (_source_file_id BIGINT)")
    for capture, year in captures.items():
        con.execute("INSERT INTO metadata.capturas VALUES (?, ?)", (capture, year))
    for capture, count in raw.items():
        con.execute("INSERT INTO raw_fonte_a.votos SELECT ? FROM range(?)", (capture, count))
    con.execute(
        "INSERT INTO metadata.fontes_verificacoes VALUES "
        "(1, 'fonte_a', 'votos', 2022, 'carga', 'lidas 5, filtradas pelo only 0, carregadas 5, rejeitadas 0'), "
        "(2, 'fonte_a', 'votos', 2022, 'carga', ?)",
        (f"lidas {carregadas}, filtradas pelo only 0, carregadas {carregadas}, rejeitadas 0",),
    )
    return con


def failures(raw: dict[int, int]) -> list[tuple[object, ...]]:
    con = warehouse({10: 2022, 11: 2022, 12: 2018}, carregadas=100, raw=raw)
    return con.execute(render(con)).fetchall()


def test_the_current_capture_alone_in_the_raw_reconciles() -> None:
    assert failures({11: 100, 12: 7}) == []


def test_a_partition_with_the_old_version_still_in_the_raw_is_doubled_and_fails() -> None:
    assert failures({10: 100, 11: 100}) == [("fonte_a", "votos", 2022, 200, 100)]


def test_a_partition_that_lost_rows_fails() -> None:
    assert failures({11: 99}) == [("fonte_a", "votos", 2022, 99, 100)]


def test_every_replace_partition_dataset_is_declared_in_the_dbt_sources_and_only_those() -> None:
    declared: set[tuple[str, str]] = set()
    for file in (DBT / "models/staging").rglob("*sources.yml"):
        for source in yaml.safe_load(file.read_text(encoding="utf-8"))["sources"]:
            for table in source["tables"]:
                if (table.get("meta") or {}).get("escrita") == "replace_partition":
                    declared.add((source["name"], table["name"]))
    expected = {
        (c.source, name)
        for c in contracts.find_all()
        for name, d in c.datasets.items()
        if d.write == "replace_partition"
    }
    assert declared == expected
