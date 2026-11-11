"""Convenção de nomes e descrições (ADR 0022) conferida no warehouse que a pipeline constrói."""

import re

from dado_publico_brasil.core.settings import Settings
from dado_publico_brasil.core.warehouse import Connection, rows
from dado_publico_brasil.ingestion import contract as contracts
from dado_publico_brasil.transformation import catalog, colecoes

CONVENTION = "docs/03-consultar/02-convencao-de-nomes.md"
OWN_LAYERS = ("staging", "intermediate", "marts", "identity", "metadata")
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
        "'intermediate', 'marts', 'identity', 'metadata')",
    )
    wrong = []
    for r in names:
        theme = re.sub(r"^(stg_[a-z]+__|int_)", "", r["table_name"])
        if CONNECTIVES & set(theme.split("_")):
            wrong.append(f"{r['schema_name']}.{r['table_name']}")
    assert wrong == [], f"nomes de tabela com conectivo ({CONVENTION}): {wrong}"


def test_source_staging_and_marts_carry_the_audit_columns_and_the_standard_meta(
    full: tuple[Connection, Settings],
) -> None:
    """ADR 0035: staging de fonte (5 colunas) e dim_/fct_/brg_ (3) rastreáveis até a captura; toda tabela com meta padrão."""
    nodes = [
        n
        for n in catalog.manifest(full[1])["nodes"].values()
        if n["resource_type"] in ("model", "seed") and n["package_name"] == "dado_publico_brasil"
    ]
    have: dict[str, set[str]] = {}
    for c in columns(full[0], OWN_LAYERS):
        have.setdefault(f"{c['schema_name']}.{c['table_name']}", set()).add(c["column_name"])
    missing: list[str] = []
    bad_meta: list[str] = []
    for n in nodes:
        meta, name, layer = n["meta"], n["name"], n["fqn"][1]
        bad_meta += [f"{name}.{k}" for k in ("owner", "sensitivity", "fonte_oficial") if not meta.get(k)]
        if meta.get("auditoria_excecao"):
            continue
        need = (
            ("fonte", "id_captura", "dt_captura", "url_fonte", "sha256_captura")
            if layer == "staging"
            else ("fonte", "id_captura", "dt_captura")
            if layer == "marts" and name.startswith(("dim_", "fct_", "brg_"))
            else ()
        )
        missing += [
            f"{name}.{c}" for c in need if c not in have.get(f"{n['schema']}.{n.get('alias') or name}", set())
        ]
    assert missing == [], f"sem colunas de auditoria (ADR 0035; ou declare meta.auditoria_excecao): {missing}"
    assert bad_meta == [], f"meta fora do padrão (owner, sensitivity, fonte_oficial): {bad_meta}"


def test_file_collections_follow_the_convention() -> None:
    """Tabelas de controle `arq_<colecao>` (ADR 0037): nome sem conectivo, colunas com prefixo de tipo e descritas."""
    wrong: list[str] = []
    for source in contracts.find_all():
        for dataset in source.datasets.values():
            if dataset.arquivos:
                name = f"arq_{dataset.arquivos.colecao}"
                wrong += [f"{name}: conectivo"] if CONNECTIVES & set(name.split("_")) else []
    for name, kind, description in colecoes.CONTROL_COLUMNS:
        if kind.startswith(("DATE", "TIMESTAMP")) != name.startswith("dt_") or (
            kind == "BOOLEAN"
        ) != name.startswith("fl_"):
            wrong.append(f"{name} ({kind}): prefixo")
        if not description:
            wrong.append(f"{name}: sem descrição")
    assert colecoes.CONTROL_DESCRIPTION % "x" and wrong == [], (
        f"arq_ fora da convenção ({CONVENTION}): {wrong}"
    )
