"""Definições do Dagster: o pipeline como ativos, com linhagem e agendamento diário incremental.

    landing_<fonte> (arquivos) -> raw_<fonte> (dlt) -> dbt staging e intermediate (tag pre_identity)
        -> identity.* (código próprio) -> dbt intermediate restante e marts

Os ativos de cada fonte saem de `sources/` (uma fonte nova não pede código aqui). O dbt entra como ativos
(um por modelo); as fontes do dbt têm a mesma chave dos ativos do raw (`<fonte>/<tabela>`), então a
dependência vem da declaração do dbt. Carga histórica ou incremental é só a configuração do landing.
"""

import os
from collections.abc import Iterator
from typing import Any

from dagster import (
    AssetExecutionContext,
    AssetKey,
    AssetsDefinition,
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
from plataforma_dados.ingestion import contract, landing, loader
from plataforma_dados.orchestration import pipeline
from plataforma_dados.transformation import build

SETTINGS = load_settings()
os.environ["PLATAFORMA_WAREHOUSE_FILE"] = str(SETTINGS.warehouse.resolve())
PROJECT = DbtProject(
    project_dir=DBT_DIR,
    profiles_dir=DBT_DIR,
    target_path=SETTINGS.state_dir / "dbt" / "target",
)
PROJECT.prepare_if_dev()

PEOPLE = [AssetKey(["identity", "pessoa"]), AssetKey(["identity", "pessoa_identificador"])]
IDS_MODEL = AssetKey("int_pessoas_ids_vistos")


class ExtractionConfig(Config):
    """Escolhe o que extrair. `incremental` (padrão) é o do agendamento diário."""

    mode: str = "incremental"  # incremental | historical | years
    from_year: int | None = None
    to_year: int | None = None
    years: list[int] = []
    extra_years: list[int] = []
    force: bool = False


def _plan(config: ExtractionConfig) -> pipeline.Plan:
    if config.mode == "historical":
        return lambda c: landing.plan_historical(
            c, config.from_year or 2000, config.to_year, config.extra_years
        )
    if config.mode == "years":
        return lambda c: landing.plan(c, config.years, config.extra_years)
    return landing.plan_incremental


def _source_assets(source: contract.SourceContract) -> list[AssetsDefinition]:
    captured = AssetKey(["landing", source.source])
    raw_tables = [AssetKey([source.source, loader.normalize(name)]) for name in source.datasets]

    @asset(key=captured, group_name="landing")
    def landing_asset(config: ExtractionConfig) -> MaterializeResult[Any]:
        """Arquivos da fonte, intactos, com hash e data."""
        con = migrations.open_warehouse(SETTINGS)
        try:
            n = landing.extract_plan(con, SETTINGS, source, _plan(config)(source), force=config.force)
        finally:
            con.close()
        return MaterializeResult(metadata={"datasets": n, "mode": config.mode})

    @multi_asset(
        specs=[AssetSpec(key=k, group_name="raw", deps=[captured]) for k in raw_tables],
        name=f"raw_{source.source}",
    )
    def raw_asset() -> Iterator[MaterializeResult[Any]]:
        """O dlt carrega todos os arquivos novos; as tabelas do raw saem juntas."""
        con = migrations.open_warehouse(SETTINGS)
        try:
            captures, rows = loader.load_pending(con, SETTINGS, source)
        finally:
            con.close()
        for key in raw_tables:
            yield MaterializeResult(asset_key=key, metadata={"captures": captures, "rows_total": rows})

    return [landing_asset, raw_asset]


@dbt_assets(manifest=PROJECT.manifest_path, select="tag:pre_identity", name="dbt_pre_identity")
def dbt_pre_identity(context: AssetExecutionContext, dbt: DbtCliResource) -> Iterator[Any]:
    yield from dbt.cli(["build", "--indirect-selection", "cautious"], context=context).stream()


@multi_asset(
    specs=[AssetSpec(key=k, group_name="identity", deps=[IDS_MODEL]) for k in PEOPLE],
    name="identity",
)
def identity_asset() -> Iterator[MaterializeResult[Any]]:
    created = build.resolve_identity(SETTINGS)
    for key in PEOPLE:
        yield MaterializeResult(asset_key=key, metadata={"created": created})


@dbt_assets(manifest=PROJECT.manifest_path, exclude="tag:pre_identity", name="dbt_post_identity")
def dbt_post_identity(context: AssetExecutionContext, dbt: DbtCliResource) -> Iterator[Any]:
    yield from dbt.cli(["build", "--indirect-selection", "cautious"], context=context).stream()


daily = define_asset_job("daily_pipeline", selection="*")

defs = Definitions(
    assets=[
        *(a for source in contract.find_all() for a in _source_assets(source)),
        dbt_pre_identity,
        identity_asset,
        dbt_post_identity,
    ],
    jobs=[daily],
    schedules=[ScheduleDefinition(job=daily, cron_schedule="0 6 * * *", name="daily_incremental")],
    resources={"dbt": DbtCliResource(project_dir=PROJECT, profiles_dir=str(DBT_DIR))},
)
