"""Garantias do repositório: catálogo em dia, fronteiras entre os motores e definições do Dagster carregáveis."""

import ast
import os
import subprocess
import sys
from pathlib import Path

import pytest

from dado_publico_brasil.core.settings import Settings
from dado_publico_brasil.transformation import catalog, dbt

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "03-consultar" / "01-catalogo.md"


def test_catalog_document_is_up_to_date_with_the_dbt_project() -> None:
    assert DOC.read_text(encoding="utf-8") == catalog.markdown(Settings()), (
        "docs/03-consultar/01-catalogo.md desatualizado: rode `uv run dado-publico catalog`"
    )


def test_catalog_covers_every_table_the_pipeline_builds() -> None:
    names = {(t["schema"], t["name"]) for t in catalog.tables(Settings())}
    assert ("marts", "pessoas") in names
    assert ("staging", "stg_camara__votos") in names
    assert ("raw_federal_camara", "votacoes_votos") in names
    assert ("identity", "pessoa") in names
    assert all(t["description"] for t in catalog.tables(Settings()))


SENSITIVITIES = {"publico", "publico-agente-publico", "publico-dados-pessoais-de-terceiros", "controle"}


def test_sensitivity_is_declared_from_the_known_classes_and_a_table_with_personal_columns_is_not_public() -> (
    None
):
    settings = Settings()
    invalid = [t["name"] for t in catalog.tables(settings) if t["sensitivity"] not in SENSITIVITIES]
    assert not invalid, f"tabelas sem sensibilidade conhecida: {invalid}"
    sensitivity = {t["name"]: t["sensitivity"] for t in catalog.tables(settings) if t["schema"] == "marts"}
    wrong = sorted(
        {c["table"] for c in catalog.columns(settings) if c["pii"] and sensitivity[c["table"]] == "publico"}
    )
    assert not wrong, f"tabelas com coluna de dado pessoal marcadas como públicas: {wrong}"


def test_every_mart_column_has_a_description() -> None:
    cols = catalog.columns(Settings())
    assert cols
    missing = [f"{c['table']}.{c['name']}" for c in cols if not c["description"]]
    assert not missing, f"colunas dos marts sem descrição: {missing}"


# Quem pode importar quem: ingestão e transformação só conhecem o núcleo (a fronteira entre elas é o schema
# raw e metadata.captures); só a orquestração conhece os dois motores; nada daqui conhece as aplicações.
ALLOWED = {
    "core": set(),
    "ingestion": {"core"},
    "transformation": {"core"},
    "documents": {"core"},
    "orchestration": {"core", "ingestion", "transformation", "documents"},
}
SRC = ROOT / "src" / "dado_publico_brasil"


def _imports(folder: Path) -> set[str]:
    found: set[str] = set()
    for file in folder.rglob("*.py"):
        for node in ast.walk(ast.parse(file.read_text(encoding="utf-8"))):
            modules = [a.name for a in node.names] if isinstance(node, ast.Import) else []
            if isinstance(node, ast.ImportFrom) and node.module:
                modules = [node.module]
            found |= set(modules)
    return found


@pytest.mark.parametrize("package", sorted(ALLOWED))
def test_subpackages_only_import_what_the_architecture_allows(package: str) -> None:
    prefix = "dado_publico_brasil."
    imported = {m.split(".")[1] for m in _imports(SRC / package) if m.startswith(prefix)} - {package}
    assert imported <= ALLOWED[package], f"{package} importa {sorted(imported - ALLOWED[package])}"


def test_the_platform_does_not_import_any_application() -> None:
    assert not {m for m in _imports(SRC) if m.startswith("quem_decidiu")}


def test_dagster_definitions_load_with_the_expected_assets(tmp_path: Path) -> None:
    settings = Settings(storage_root=tmp_path / "store")
    dbt.invoke(settings, "parse")  # gera o manifesto que o Dagster lê
    code = (
        "from dagster import AssetKey;"
        "from dado_publico_brasil.ingestion import contract;"
        "from dado_publico_brasil.orchestration.definitions import defs;"
        "graph = defs.resolve_asset_graph();"
        "keys = {k.to_user_string() for k in graph.get_all_asset_keys()};"
        "scheduled = sorted(s.source for s in contract.find_all() if s.schedule);"
        "print(len(keys), 'marts/pessoas' in keys, 'identity/pessoa' in keys, {'landing/camara', 'landing/senado'} <= keys,"
        " sorted(s.name for s in defs.schedules or []) == [f'captura_{n}' for n in scheduled],"
        " sorted(j.name for j in defs.jobs or []) ==  sorted(['atualizar_tudo', 'capturar_tudo', 'processar_tudo'] + [f'{p}_{c.source}' for c in contract.find_all() for p in ('atualizar', 'captura')]),"
        " sorted(s.name for s in defs.sensors or []),"
        " graph.get(AssetKey(['marts', 'pessoas'])).automation_condition is not None,"
        " graph.get(AssetKey(['identity', 'pessoa'])).automation_condition is not None,"
        " graph.get(AssetKey(['tse', 'candidaturas'])).automation_condition is None,"
        " len([c for c in graph.asset_check_keys if c.name == 'saude_da_fonte']) > 0,"
        " defs.resolve_job_def('atualizar_tudo').tags.get('dado_publico/refazer') == 'true'"
        " and 'dado_publico/refazer' not in defs.resolve_job_def('captura_camara').tags,"
        " {a.specs_by_key[k].group_name for a in [d for d in defs.assets if hasattr(d, 'specs_by_key')] for k in a.keys if k.path[0] in ('staging', 'intermediate', 'marts')}"
        " <= {'staging', 'intermediate', 'core', 'fatos', 'marts', 'seeds'},"
        " len([c for c in graph.asset_check_keys if c.asset_key.path[0] == 'landing' and c.name != 'saude_da_fonte']) == len(scheduled))"
    )
    env = {**os.environ, "DADO_PUBLICO_STORAGE_ROOT": str(settings.storage_root)}
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, env=env, cwd=ROOT, check=False
    )
    assert result.returncode == 0, result.stderr[-1500:]
    sensors = "['falha_de_execucao', 'propagar_atualizacoes', 'verificar_atrasos']"
    # ativos; agendamento e job por fonte; sensores; dbt e identidade sobem sozinhos, o raw não; atraso por fonte agendada
    assert f"True True True True True {sensors} True True True True True True True" in result.stdout, (
        result.stdout
    )
