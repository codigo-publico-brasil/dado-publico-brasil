"""Definições do Dagster: o pipeline como ativos, com linhagem, agendamento por fonte e propagação automática.

    landing_<fonte> (arquivos) -> raw_<fonte> (dlt) -> dbt staging e intermediate (tag pre_identity)
        -> identity.* (código próprio) -> dbt intermediate restante e marts

Os ativos de cada fonte saem de `sources/` (uma fonte nova não pede código aqui). O dbt entra como ativos
(um por modelo); as fontes do dbt têm a mesma chave dos ativos do raw (`<fonte>/<tabela>`), então a
dependência vem da declaração do dbt. Carga histórica ou incremental é só a configuração do landing.

Automação (ADR 0027): cada fonte com `schedule` no YAML ganha um agendamento que roda o job `captura_<fonte>`
(landing e raw); o que depende do raw (dbt, identidade, publicação) roda sozinho quando o raw recebe dado novo
(`AutomationCondition.eager`). `atualizar_<fonte>` refaz tudo o que vem da fonte; `atualizar_tudo` refaz tudo.
"""

import json
import os
from collections.abc import Iterator, Mapping
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from croniter import croniter  # type: ignore[import-untyped]  # já vem com o Dagster
from dagster import (
    AssetCheckResult,
    AssetCheckSeverity,
    AssetCheckSpec,
    AssetExecutionContext,
    AssetKey,
    AssetsDefinition,
    AssetSelection,
    AssetSpec,
    AutomationCondition,
    AutomationConditionSensorDefinition,
    Config,
    DefaultScheduleStatus,
    DefaultSensorStatus,
    Definitions,
    MaterializeResult,
    RunFailureSensorContext,
    ScheduleDefinition,
    asset,
    build_last_update_freshness_checks,
    build_sensor_for_freshness_checks,
    define_asset_job,
    in_process_executor,
    multi_asset,
    multi_asset_check,
    run_failure_sensor,
)
from dagster_dbt import DagsterDbtTranslator, DbtCliResource, DbtProject, dbt_assets

from dado_publico_brasil.core import alert, migrations, runs, warehouse
from dado_publico_brasil.core.settings import DBT_DIR, load_settings
from dado_publico_brasil.ingestion import contract, landing, loader, monitoring
from dado_publico_brasil.orchestration import pipeline
from dado_publico_brasil.transformation import build, describe, observability, publish, quality
from dado_publico_brasil.transformation import dbt as dbt_runner

SETTINGS = load_settings()
os.environ["DADO_PUBLICO_WAREHOUSE_FILE"] = str(SETTINGS.warehouse.resolve())
DBT_TARGET = SETTINGS.state_dir / "dbt" / "dagster"  # artefatos do dbt fora do repositório
PROJECT = DbtProject(
    project_dir=DBT_DIR, profiles_dir=DBT_DIR, target_path=SETTINGS.state_dir / "dbt" / "target"
)
PROJECT.prepare_if_dev()

TIMEZONE = "America/Sao_Paulo"  # fuso dos `schedule` das fontes
EAGER = AutomationCondition.eager()  # roda quando uma dependência recebe dado novo


class LayerTranslator(DagsterDbtTranslator):
    """Grupo = camada do dbt (staging, intermediate, marts) e execução automática quando o upstream muda."""

    def get_group_name(self, dbt_resource_props: Mapping[str, Any]) -> str | None:
        return str(dbt_resource_props["fqn"][1])

    def get_automation_condition(
        self, dbt_resource_props: Mapping[str, Any]
    ) -> AutomationCondition[Any] | None:
        return EAGER


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
    raw = {AssetKey([source.source, loader.normalize(n)]): n for n, d in source.datasets.items() if d.raw}
    raw_tables = list(raw)

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
        specs=[AssetSpec(key=k, group_name="raw", deps=[captured], skippable=True) for k in raw_tables],
        name=f"raw_{source.source}",
    )
    def raw_asset() -> Iterator[MaterializeResult[Any]]:
        """O dlt carrega todos os arquivos novos; as tabelas do raw saem juntas.

        Sem captura nova nada é registrado: o que depende do raw só roda quando há dado novo.
        """
        con = migrations.open_warehouse(SETTINGS)
        try:
            captures, rows = loader.load_pending(con, SETTINGS, source)
        finally:
            con.close()
        if captures:
            for key in raw_tables:
                yield MaterializeResult(asset_key=key, metadata={"captures": captures, "rows_total": rows})

    @multi_asset_check(
        specs=[AssetCheckSpec("saude_da_fonte", asset=key) for key in raw_tables],
        name=f"saude_{source.source}",
    )
    def source_health() -> Iterator[AssetCheckResult]:
        """O último monitor da fonte e o balanço da carga de cada tabela (`metadata.source_checks`)."""
        con = warehouse.connect(SETTINGS, read_only=True)
        try:
            for key, name in raw.items():
                status, details = monitoring.latest_status(con, source.source, name)
                yield AssetCheckResult(
                    check_name="saude_da_fonte",
                    asset_key=key,
                    passed=status == "ok",
                    severity=AssetCheckSeverity.ERROR if status == "error" else AssetCheckSeverity.WARN,
                    metadata={"detalhes": chr(10).join(details) or "sem alertas"},
                )
        finally:
            con.close()

    return [landing_asset, raw_asset, source_health]


def _keys(source: contract.SourceContract) -> list[AssetKey]:
    return [
        AssetKey(["landing", source.source]),
        *(AssetKey([source.source, loader.normalize(n)]) for n, d in source.datasets.items() if d.raw),
    ]


def _cadence_slack(cron: str) -> timedelta:
    """Uma vez e meia o intervalo do `schedule`: passou disso sem captura, a fonte está atrasada."""
    start = croniter(cron, datetime(2026, 1, 5))
    first, second = start.get_next(datetime), start.get_next(datetime)
    return timedelta(seconds=(second - first).total_seconds() * 1.5)


def _record_dbt(stage: str, target: Path) -> None:
    """Grava o resultado dos modelos e testes em `metadata.dbt_results`, como a linha de comando faz."""
    con = warehouse.connect(SETTINGS)
    try:
        with runs.track(con, stage, "dbt") as run:
            results = dbt_runner.read_results(SETTINGS, target=target)
            quality.record(con, run.id, results)
            run.rows_in = len(results)
            if stage == "transform_post":
                describe.raw(con, target)
                observability.notify(con)
    finally:
        con.close()


@dbt_assets(
    manifest=PROJECT.manifest_path,
    select="tag:pre_identity",
    name="dbt_pre_identity",
    dagster_dbt_translator=LayerTranslator(),
)
def dbt_pre_identity(context: AssetExecutionContext, dbt: DbtCliResource) -> Iterator[Any]:
    invocation = dbt.cli(
        ["build", "--indirect-selection", "cautious"], context=context, target_path=DBT_TARGET
    )
    yield from invocation.stream()
    _record_dbt("transform_pre", invocation.target_path)


@multi_asset(
    specs=[
        AssetSpec(key=k, group_name="identity", deps=[IDS_MODEL], automation_condition=EAGER) for k in PEOPLE
    ],
    name="identity",
)
def identity_asset() -> Iterator[MaterializeResult[Any]]:
    created = build.resolve_identity(SETTINGS)
    for key in PEOPLE:
        yield MaterializeResult(asset_key=key, metadata={"created": created})


@dbt_assets(
    manifest=PROJECT.manifest_path,
    exclude="tag:pre_identity",
    name="dbt_post_identity",
    dagster_dbt_translator=LayerTranslator(),
)
def dbt_post_identity(context: AssetExecutionContext, dbt: DbtCliResource) -> Iterator[Any]:
    invocation = dbt.cli(
        ["build", "--indirect-selection", "cautious"], context=context, target_path=DBT_TARGET
    )
    yield from invocation.stream()
    _record_dbt("transform_post", invocation.target_path)


@run_failure_sensor(name="falha_de_execucao", default_status=DefaultSensorStatus.RUNNING)
def failure_email(context: RunFailureSensorContext) -> None:
    """Avisa por e-mail quando qualquer execução falha (o e-mail da fase de marts só sai se ela chegar lá)."""
    run, base = context.dagster_run, os.environ.get("DADO_PUBLICO_DAGSTER_URL")
    steps = [e.step_key for e in context.get_step_failure_events() if e.step_key]
    url = f"{base.rstrip('/')}/runs/{run.run_id}" if base else None
    alert.notify_failure(run.job_name, run.run_id, steps, context.failure_event.message or "", url)


def _marts() -> list[AssetKey]:
    """Os modelos da camada marts, que o `publish` copia para o PostgreSQL."""
    nodes = json.loads(PROJECT.manifest_path.read_text(encoding="utf-8"))["nodes"].values()
    return [AssetKey([n["schema"], n["name"]]) for n in nodes if n["resource_type"] == "model" and n["fqn"][1] == "marts"]


@asset(key=AssetKey(["servico", "marts"]), deps=_marts(), group_name="servico", automation_condition=EAGER)
def publish_asset() -> MaterializeResult[Any]:
    """Copia os marts para o PostgreSQL de serviço, numa troca atômica (ADR 0014)."""
    tables = publish.publish(SETTINGS)
    return MaterializeResult(metadata={"tabelas": len(tables), "linhas": sum(tables.values())})


SOURCES = contract.find_all()
SCHEDULED = [s for s in SOURCES if s.schedule]
EXTRA = (
    [publish_asset] if SETTINGS.service_dsn else []
)  # sem o banco de serviço configurado, não há o que publicar
jobs = [
    define_asset_job("atualizar_tudo", selection="*"),
    *(
        define_asset_job(f"atualizar_{s.source}", selection=AssetSelection.assets(*_keys(s)).downstream())
        for s in SOURCES
    ),
    *(define_asset_job(f"captura_{s.source}", selection=AssetSelection.assets(*_keys(s))) for s in SOURCES),
]
schedules = [
    ScheduleDefinition(
        name=f"captura_{s.source}",
        job_name=f"captura_{s.source}",
        cron_schedule=str(s.schedule),
        execution_timezone=TIMEZONE,
        default_status=DefaultScheduleStatus.RUNNING,
    )
    for s in SCHEDULED
]
freshness = [
    check
    for s in SCHEDULED
    for check in build_last_update_freshness_checks(
        assets=[AssetKey(["landing", s.source])],
        lower_bound_delta=_cadence_slack(str(s.schedule)),
        deadline_cron=str(s.schedule),
        timezone=TIMEZONE,
    )
]
sensors = [
    failure_email,
    AutomationConditionSensorDefinition(
        "propagar_atualizacoes", target=AssetSelection.all(), default_status=DefaultSensorStatus.RUNNING
    ),
    build_sensor_for_freshness_checks(
        freshness_checks=freshness, name="verificar_atrasos", default_status=DefaultSensorStatus.RUNNING
    ),
]

defs = Definitions(
    assets=[
        *(a for source in SOURCES for a in _source_assets(source)),
        dbt_pre_identity,
        identity_asset,
        dbt_post_identity,
        *EXTRA,
    ],
    asset_checks=freshness,
    jobs=jobs,
    sensors=sensors,
    schedules=schedules,
    # O DuckDB em arquivo aceita um escritor por vez: os passos rodam em sequência, num processo só.
    executor=in_process_executor,
    resources={"dbt": DbtCliResource(project_dir=PROJECT, profiles_dir=str(DBT_DIR))},
)
