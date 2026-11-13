"""Trava pelo plano de execução: nenhum modelo dbt pode juntar por laço aninhado ou produto cartesiano.

O dbt compila cada modelo no warehouse sintético completo e o DuckDB explica o plano. Junção por `in (f(a), f(b))`
ou por `or` não vira hash join: o DuckDB cai em `BLOCKWISE_NL_JOIN` (quadrático; travou o `fct_emendas` em produção).
Nomes dos operadores: `PhysicalOperatorType` em
https://github.com/duckdb/duckdb/blob/main/src/include/duckdb/common/enums/physical_operator_type.hpp
(conferidos no `EXPLAIN (FORMAT json)` do DuckDB 2.0 travado no uv.lock).
Exceção legítima (tabela de apoio minúscula) entra em ALLOWED com o motivo.
"""

import json
import shutil
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import duckdb
import pytest

from dado_publico_brasil.core.settings import Settings
from dado_publico_brasil.transformation import dbt

BAD = ("NESTED_LOOP_JOIN", "BLOCKWISE_NL_JOIN", "CROSS_PRODUCT")
# (modelo, operador) -> motivo em uma linha; sem motivo não entra. O custo é o do lado grande vezes o lado minúsculo.
_CORTES = "cortes: ~60 datas (2 por ano desde 1997 e a posse de cada legislatura), lado minúsculo e fixo"
ALLOWED: dict[tuple[str, str], str] = {
    ("agg_composicoes", "BLOCKWISE_NL_JOIN"): _CORTES,
    ("agg_composicoes", "NESTED_LOOP_JOIN"): _CORTES + " (no volume real o ASOF/IE do DuckDB assume)",
    ("dim_disputas", "BLOCKWISE_NL_JOIN"): "`tipo = 'pais'` em dim_territorios tem uma só linha (Brasil)",
    ("fct_proposicoes", "CROSS_PRODUCT"): "`siglas` é um agregado de uma só linha (lista de siglas)",
    ("int_votacoes_votos_ligados", "NESTED_LOOP_JOIN"): "legislaturas: ~57 linhas contra os votos do Senado",
}

# O padrão que travou o `fct_emendas` (ligação da pessoa por nome): chave calculada nos dois lados dentro de `in`.
OLD_JOIN = """
select a.cd_autor, p.id_pessoa
from (select cd_autor, ano, any_value(name_key(autor_nome)) as nome_chave
      from staging.stg_transparencia__emendas group by cd_autor, ano) as a
inner join marts.dim_pessoas as p on a.nome_chave in (name_key(p.nome_publico), name_key(p.nome_civil))
"""


def bad_operators(con: duckdb.DuckDBPyConnection, sql: str) -> list[tuple[str, str]]:
    """(operador, trecho do plano) de cada junção que não escala no `EXPLAIN` do SQL."""
    plan = json.loads(con.execute(f"EXPLAIN (FORMAT json) {sql}").fetchall()[-1][1])
    found: list[tuple[str, str]] = []

    def walk(node: dict[str, Any]) -> None:
        if node["name"] in BAD:
            found.append((node["name"], json.dumps(node["extra_info"], ensure_ascii=False)[:400]))
        for child in node["children"]:
            walk(child)

    for root in plan:
        walk(root)
    return found


@pytest.fixture(scope="module")
def compiled(
    snapshots: dict[str, Path], tmp_path_factory: pytest.TempPathFactory
) -> Iterator[tuple[duckdb.DuckDBPyConnection, dict[str, str]]]:
    """Warehouse sintético completo (só leitura) e o SQL compilado de cada modelo do projeto."""
    store = tmp_path_factory.mktemp("plans") / "store"
    shutil.copytree(snapshots["full"], store)
    settings = Settings(storage_root=store)
    outcome = dbt.invoke(settings, "compile")
    assert outcome.returncode == 0, outcome.output
    nodes = json.loads((dbt.target_dir(settings) / "manifest.json").read_text(encoding="utf-8"))["nodes"]
    sql = {
        n["name"]: (
            dbt.target_dir(settings) / "compiled" / n["package_name"] / n["original_file_path"]
        ).read_text(encoding="utf-8")
        for n in nodes.values()
        if n["resource_type"] == "model" and n["package_name"] == "dado_publico_brasil"
    }
    con = duckdb.connect(str(settings.warehouse), read_only=True)
    con.execute(f"ATTACH '{settings.registry}' AS registry (READ_ONLY)")
    yield con, sql
    con.close()


def test_the_old_name_join_is_flagged_by_the_plan(
    compiled: tuple[duckdb.DuckDBPyConnection, dict[str, str]],
) -> None:
    con, _ = compiled
    assert [op for op, _ in bad_operators(con, OLD_JOIN)] == ["BLOCKWISE_NL_JOIN"]


def test_no_model_joins_by_nested_loop_or_cross_product(
    compiled: tuple[duckdb.DuckDBPyConnection, dict[str, str]],
) -> None:
    con, models = compiled
    assert len(models) > 100  # o compile achou os modelos do projeto
    assert all(ALLOWED.values())  # exceção sem motivo não vale
    found = [
        f"{name}: {op}\n{plan}"
        for name, sql in sorted(models.items())
        for op, plan in bad_operators(con, sql)
        if (name, op) not in ALLOWED
    ]
    assert not found, (
        "junção que não escala (ligue por igualdade em chave calculada uma vez, ou declare em ALLOWED):\n"
        + "\n".join(found)
    )
