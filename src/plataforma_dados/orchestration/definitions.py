"""Definições do Dagster: o pipeline como ativos, com linhagem e agendamento diário incremental.

    metadata.captures (landing) -> raw_federal_camara.* (dlt) -> dbt staging e intermediate (tag pre_identity)
        -> identity.* (código próprio) -> dbt intermediate restante e marts

O dbt entra como ativos (um por modelo). As fontes do dbt têm a mesma chave dos ativos que as
produzem (`<fonte>/<tabela>`), então a dependência vem da declaração do dbt. Carga histórica ou
incremental é só a configuração do primeiro ativo.
"""

import os
from collections.abc import Iterator
from typing import Any

from dagster import (
    AssetExecutionContext,
    AssetKey,
    AssetSpec,
    Config,
    Definitions,
    MaterializeResult,
    ScheduleDefinition,
    asset,
    define_asset_job,
    multi_asset,
)
from dagster_dbt import DbtCliResource, DbtProject, dbt_assets

from plataforma_dados.core import migrations
from plataforma_dados.core.settings import DBT_DIR, load_settings
from plataforma_dados.ingestion import landing, loader
from plataforma_dados.orchestration import pipeline
from plataforma_dados.transformation import build

SETTINGS = load_settings()
os.environ["PLATAFORMA_WAREHOUSE_FILE"] = str(SETTINGS.warehouse.resolve())
CONTRACT = pipeline.contract_of()
PROJECT = DbtProject(
    project_dir=DBT_DIR,
    profiles_dir=DBT_DIR,
    target_path=SETTINGS.state_dir / "dbt" / "target",
)
PROJECT.prepare_if_dev()

CAPTURES = AssetKey(["metadata", "captures"])
RAW_TABLES = [AssetKey([CONTRACT.source, loader.normalize(name)]) for name in CONTRACT.datasets]
PEOPLE = [AssetKey(["identity", "pessoa"]), AssetKey(["identity", "pessoa_identificador"])]
IDS_MODEL = AssetKey("int_deputados_ids_unidos")


class ExtractionConfig(Config):
    """Escolhe o que extrair. `incremental` (padrão) é o do agendamento diário."""

    mode: str = "incremental"  # incremental | historical | years
    from_year: int | None = None
    to_year: int | None = None
    years: list[int] = []
    extra_years: list[int] = []
    force: bool = False


def _items(config: ExtractionConfig) -> list[landing.Item]:
    if config.mode == "historical":
        return landing.plan_historical(CONTRACT, config.from_year or 2001, config.to_year, config.extra_years)
    if config.mode == "years":
        return landing.plan(CONTRACT, config.years, config.extra_years)
    return landing.plan_incremental(CONTRACT)


@asset(key=CAPTURES, group_name="landing", description="Arquivos da fonte, intactos, com hash e data")
def landing_camara(config: ExtractionConfig) -> MaterializeResult[Any]:
    con = migrations.open_warehouse(SETTINGS)
    try:
        n = landing.extract_plan(con, SETTINGS, CONTRACT, _items(config), force=config.force)
    finally:
        con.close()
    return MaterializeResult(metadata={"datasets": n, "mode": config.mode})


@multi_asset(
    specs=[AssetSpec(key=k, group_name="raw", deps=[CAPTURES]) for k in RAW_TABLES],
    name="raw_camara",
)
def raw_camara() -> Iterator[MaterializeResult[Any]]:
    """O dlt carrega todos os arquivos novos; as tabelas do raw saem juntas."""
    con = migrations.open_warehouse(SETTINGS)
    try:
        captures, rows = loader.load_pending(con, SETTINGS, CONTRACT)
    finally:
        con.close()
    for key in RAW_TABLES:
        yield MaterializeResult(asset_key=key, metadata={"captures": captures, "rows_total": rows})


@dbt_assets(manifest=PROJECT.manifest_path, select="tag:pre_identity", name="dbt_pre_identity")
def dbt_pre_identity(context: AssetExecutionContext, dbt: DbtCliResource) -> Iterator[Any]:
    yield from dbt.cli(["build", "--indirect-selection", "cautious"], context=context).stream()


@multi_asset(
    specs=[AssetSpec(key=k, group_name="identity", deps=[IDS_MODEL]) for k in PEOPLE],
    name="identity_camara",
)
def identity_camara() -> Iterator[MaterializeResult[Any]]:
    created = build.resolve_identity(SETTINGS)
    for key in PEOPLE:
        yield MaterializeResult(asset_key=key, metadata={"created": created})


@dbt_assets(manifest=PROJECT.manifest_path, exclude="tag:pre_identity", name="dbt_post_identity")
def dbt_post_identity(context: AssetExecutionContext, dbt: DbtCliResource) -> Iterator[Any]:
    yield from dbt.cli(["build", "--indirect-selection", "cautious"], context=context).stream()


daily = define_asset_job("daily_pipeline", selection="*")

defs = Definitions(
    assets=[landing_camara, raw_camara, dbt_pre_identity, identity_camara, dbt_post_identity],
    jobs=[daily],
    schedules=[ScheduleDefinition(job=daily, cron_schedule="0 6 * * *", name="daily_incremental")],
    resources={"dbt": DbtCliResource(project_dir=PROJECT, profiles_dir=str(DBT_DIR))},
)
