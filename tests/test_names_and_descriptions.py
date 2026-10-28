"""Convenção de nomes e descrições (ADR 0022) conferida no warehouse que a pipeline constrói."""

import re

from dado_publico_brasil.core.warehouse import Connection, rows

CONVENTION = "docs/03-consultar/02-convencao-de-nomes.md"
OWN_LAYERS = ("staging", "intermediate", "core", "fatos", "analise", "servico", "marts")
CONNECTIVES = {
    "a",
    "ao",
    "aos",
    "de",
    "do",
    "da",
    "dos",
    "das",
    "em",
    "no",
    "na",
    "nos",
    "nas",
    "para",
    "por",
    "com",
    "sem",
}
# esquemas de terceiros ou internos: o `elementary` é do pacote do Elementary; `main` e os do sistema não são nossos
OUTSIDE = ("main", "information_schema", "pg_catalog", "elementary")


def columns(con: Connection, schemas: tuple[str, ...]) -> list[dict[str, str]]:
    marks = ",".join("?" for _ in schemas)
    return rows(
        con,
        "SELECT schema_name, table_name, column_name, data_type FROM duckdb_columns() "
        f"WHERE schema_name IN ({marks}) ORDER BY 1, 2, column_index",
        schemas,
    )


def test_every_table_and_column_has_a_description_in_every_layer(full: tuple[Connection, object]) -> None:
    con = full[0]
    missing_tables = rows(
        con,
        "SELECT schema_name || '.' || table_name AS name FROM ("
        "SELECT schema_name, table_name, comment FROM duckdb_tables() "
        "UNION ALL SELECT schema_name, view_name, comment FROM duckdb_views() WHERE NOT internal) "
        "WHERE comment IS NULL AND schema_name NOT IN ('main', 'information_schema', 'pg_catalog', 'elementary') "
        "AND schema_name NOT LIKE 'dlt\\_tmp\\_%' ESCAPE '\\' AND table_name NOT LIKE '\\_dlt\\_%' ESCAPE '\\' "
        "ORDER BY 1",
    )
    missing_columns = rows(
        con,
        "SELECT schema_name || '.' || table_name || '.' || column_name AS name FROM duckdb_columns() "
        "WHERE comment IS NULL AND NOT internal AND schema_name NOT IN ('main', 'information_schema', "
        "'pg_catalog', 'elementary') AND schema_name NOT LIKE 'dlt\\_tmp\\_%' ESCAPE '\\' "
        "AND table_name NOT LIKE '\\_dlt\\_%' ESCAPE '\\' ORDER BY 1",
    )
    assert [r["name"] for r in missing_tables] == [], f"tabelas sem descrição (veja {CONVENTION})"
    assert [r["name"] for r in missing_columns] == [], f"colunas sem descrição (veja {CONVENTION})"


def test_column_prefixes_show_the_type_in_every_layer_we_own(full: tuple[Connection, object]) -> None:
    wrong: list[str] = []
    for c in columns(full[0], OWN_LAYERS):
        where, name, kind = (
            f"{c['schema_name']}.{c['table_name']}.{c['column_name']}",
            c["column_name"],
            c["data_type"],
        )
        is_date = kind.startswith(("DATE", "TIMESTAMP"))
        if is_date != name.startswith("dt_") or (kind == "BOOLEAN") != name.startswith("fl_"):
            wrong.append(f"{where} ({kind})")
        if re.search(r"(_id|_codigo|_em)$", name) or re.match(r"(data|dt_data)_", name):
            wrong.append(f"{where}: sufixo ou prefixo fora do padrão")
    assert wrong == [], f"colunas fora da convenção ({CONVENTION}): {wrong}"


def test_table_names_have_the_theme_first_and_no_connectives(full: tuple[Connection, object]) -> None:
    names = rows(
        full[0],
        "SELECT DISTINCT schema_name, table_name FROM duckdb_columns() WHERE schema_name IN ('staging', "
        "'intermediate', 'core', 'fatos', 'analise', 'servico', 'marts')",
    )
    wrong = []
    for r in names:
        theme = re.sub(r"^(stg_[a-z]+__|int_)", "", r["table_name"])
        if CONNECTIVES & set(theme.split("_")):
            wrong.append(f"{r['schema_name']}.{r['table_name']}")
    assert wrong == [], f"nomes de tabela com conectivo ({CONVENTION}): {wrong}"
