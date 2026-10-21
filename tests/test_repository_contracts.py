"""Garantias do repositório: catálogo em dia, fronteiras entre os motores e definições do Dagster carregáveis."""

import ast
import os
import subprocess
import sys
from pathlib import Path

import pytest

from plataforma_dados.core.settings import Settings
from plataforma_dados.transformation import catalog, dbt

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "dados" / "catalogo.md"


def test_catalog_document_is_up_to_date_with_the_dbt_project() -> None:
    assert DOC.read_text(encoding="utf-8") == catalog.markdown(Settings()), (
        "docs/dados/catalogo.md desatualizado: rode `uv run plataforma catalog`"
    )


def test_catalog_covers_every_table_the_pipeline_builds() -> None:
    names = {(t["schema"], t["name"]) for t in catalog.tables(Settings())}
    assert ("marts", "pessoas") in names
    assert ("staging", "stg_camara__votos") in names
    assert ("raw_federal_camara", "votacoes_votos") in names
    assert ("identity", "pessoa") in names
    assert all(t["description"] for t in catalog.tables(Settings()))


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
SRC = ROOT / "src" / "plataforma_dados"


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
    prefix = "plataforma_dados."
    imported = {m.split(".")[1] for m in _imports(SRC / package) if m.startswith(prefix)} - {package}
    assert imported <= ALLOWED[package], f"{package} importa {sorted(imported - ALLOWED[package])}"


def test_the_platform_does_not_import_any_application() -> None:
    assert not {m for m in _imports(SRC) if m.startswith("quem_decidiu")}


def test_dagster_definitions_load_with_the_expected_assets(tmp_path: Path) -> None:
    settings = Settings(storage_root=tmp_path / "store")
    dbt.invoke(settings, "parse")  # gera o manifesto que o Dagster lê
    code = (
        "from plataforma_dados.orchestration.definitions import defs;"
        "keys = {k.to_user_string() for k in defs.resolve_asset_graph().get_all_asset_keys()};"
        "print(len(keys), 'marts/pessoas' in keys or 'pessoas' in keys, 'identity/pessoa' in keys, {'landing/camara', 'landing/senado'} <= keys,"
        " [s.name for s in defs.schedules or []])"
    )
    env = {**os.environ, "PLATAFORMA_STORAGE_ROOT": str(settings.storage_root)}
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, env=env, cwd=ROOT, check=False
    )
    assert result.returncode == 0, result.stderr[-1500:]
    assert "True True True ['daily_incremental']" in result.stdout, result.stdout
