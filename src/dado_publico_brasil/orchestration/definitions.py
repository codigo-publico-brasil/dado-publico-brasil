"""Definições do Dagster: o pipeline como ativos, com linhagem, agendamento por fonte e propagação automática.

    landing_<fonte> (arquivos) -> raw_<fonte> (dlt) -> dbt staging e intermediate (tag pre_identity)
        -> identity.* (código próprio) -> dbt intermediate restante e marts

Os ativos de cada fonte saem de `sources/` (uma fonte nova não pede código aqui). O dbt entra como ativos
(um por modelo); as fontes do dbt têm a mesma chave dos ativos do raw (`<fonte>/<tabela>`), então a
dependência vem da declaração do dbt. Carga histórica ou incremental é só a configuração do landing.

Automação (ADR 0027, alterado pelo 0042): cada fonte com `schedule` no YAML ganha um agendamento que roda
o job `captura_<fonte>` (landing e raw), de madrugada. O agendamento `processar_e_publicar` roda depois delas
o job `processar_tudo` (dbt, identidade, lake e docs; a publicação por último), se o raw recebeu dado novo.
Cada agendamento roda no máximo uma vez por dia COM SUCESSO (falha pode ser repetida). Nada a jusante dispara
por evento. `atualizar_<fonte>` refaz tudo o que vem da fonte; `atualizar_tudo` refaz tudo;
`capturar_tudo` só captura (todas as fontes);
`processar_tudo` só processa, sem capturar nada; `publicar` só publica (lake e docs).
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
    Config,
    DefaultScheduleStatus,
    DefaultSensorStatus,
    Definitions,
    MaterializeResult,
    RunFailureSensorContext,
    RunRequest,
    ScheduleDefinition,
    ScheduleEvaluationContext,
    SkipReason,
    asset,
    build_last_update_freshness_checks,
    build_sensor_for_freshness_checks,
    define_asset_job,
    in_process_executor,
    multi_asset,
    multi_asset_check,
    run_failure_sensor,
    schedule,
)
from dagster_dbt import (
    DagsterDbtTranslator,
    DagsterDbtTranslatorSettings,
    DbtCliResource,
    DbtProject,
    dbt_assets,
)

from dado_publico_brasil.core import alert, migrations, runs, warehouse
from dado_publico_brasil.core.settings import DBT_DIR, load_settings
from dado_publico_brasil.ingestion import contract, landing, loader, monitoring
from dado_publico_brasil.orchestration import pipeline
from dado_publico_brasil.orchestration.pipeline import step
from dado_publico_brasil.transformation import build, describe, export, observability, quality
from dado_publico_brasil.transformation import dbt as dbt_runner

SETTINGS = load_settings()
os.environ["DADO_PUBLICO_WAREHOUSE_FILE"] = str(SETTINGS.warehouse.resolve())
DBT_TARGET = SETTINGS.state_dir / "dbt" / "dagster"  # artefatos do dbt fora do repositório
PROJECT = DbtProject(
    project_dir=DBT_DIR, profiles_dir=DBT_DIR, target_path=SETTINGS.state_dir / "dbt" / "target"
)
PROJECT.prepare_if_dev()

REFRESH = {pipeline.REFRESH_TAG: "true"}  # nos jobs `atualizar_*`: refaz o que vem depois do raw
SOURCES = contract.find_all()
TIMEZONE = pipeline.TIMEZONE  # fuso dos `schedule` das fontes


class LayerTranslator(DagsterDbtTranslator):
    """Grupo = camada do dbt (staging, intermediate, marts); tabela aninhada do dlt = ativo do dataset."""

    def get_asset_key(self, dbt_resource_props: Mapping[str, Any]) -> AssetKey:
        key = super().get_asset_key(dbt_resource_props)
        if dbt_resource_props["resource_type"] != "source":
            return key
        # o dlt grava `dataset__filho` junto com o dataset; sem isto o Dagster cria um stub sem op
        raw = {
            AssetKey([s.source, loader.normalize(n)]) for s in SOURCES for n, d in s.datasets.items() if d.raw
        }
        parts = key.path[1].split("__")
        for i in range(len(parts), 0, -1):
            parent = AssetKey([key.path[0], "__".join(parts[:i])])
            if parent in raw:
                return parent
        return key

    def get_group_name(self, dbt_resource_props: Mapping[str, Any]) -> str | None:
        if dbt_resource_props["resource_type"] == "seed":  # o `fqn` de um seed é só o nome dele
            return "seeds"
        return str(dbt_resource_props["fqn"][1])


# várias tabelas aninhadas do dlt apontam ao mesmo ativo (o do dataset), então as chaves de source repetem
TRANSLATOR = LayerTranslator(DagsterDbtTranslatorSettings(enable_duplicate_source_asset_keys=True))
PEOPLE = [AssetKey(["identity", n]) for n in ("pessoas", "pessoas_identificadores", "pessoas_fusoes")]
IDS_MODEL = AssetKey(["intermediate", "int_pessoas_ids_vistos"])  # a chave do dbt inclui a camada


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
    def landing_asset(context: AssetExecutionContext, config: ExtractionConfig) -> MaterializeResult[Any]:
        """Arquivos da fonte, intactos, com hash e data."""
        con = migrations.open_warehouse(SETTINGS)
        try:
            with step(context, f"landing {source.source} ({config.mode})"):
                n = landing.extract_plan(
                    con,
                    SETTINGS,
                    source,
                    _plan(config)(source),
                    force=config.force,
                    recover=config.mode == "incremental",
                )
        finally:
            con.close()
        context.log.info(f"landing {source.source}: {n} datasets verificados")
        return MaterializeResult(metadata={"datasets": n, "mode": config.mode})

    @multi_asset(
        specs=[AssetSpec(key=k, group_name="raw", deps=[captured], skippable=True) for k in raw_tables],
        name=f"raw_{source.source}",
    )
    def raw_asset(context: AssetExecutionContext) -> Iterator[MaterializeResult[Any]]:
        """O dlt carrega todos os arquivos novos; as tabelas do raw saem juntas.

        Sem captura nova nada é registrado, e o que depende do raw só roda quando há dado novo, salvo nos jobs
        `atualizar_*` (que pedem para refazer) e na primeira vez (o Dagster ainda não conhece o ativo).
        """
        con = migrations.open_warehouse(SETTINGS)
        try:
            with step(context, f"raw {source.source}"):
                captures, rows = loader.load_pending(con, SETTINGS, source, log=context.log.info)
        finally:
            con.close()
        refresh = context.run.tags.get(pipeline.REFRESH_TAG) == "true"
        never = any(context.instance.get_latest_materialization_event(k) is None for k in raw_tables)
        if pipeline.registers_update(captures, refresh, never):
            for key in raw_tables:
                yield MaterializeResult(asset_key=key, metadata={"captures": captures, "rows_total": rows})

    @multi_asset_check(
        specs=[AssetCheckSpec("saude_da_fonte", asset=key) for key in raw_tables],
        name=f"saude_{source.source}",
    )
    def source_health() -> Iterator[AssetCheckResult]:
        """O último monitor da fonte e o balanço da carga de cada tabela (`metadata.fontes_verificacoes`)."""
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


def _record_dbt(stage: str, target: Path, context: AssetExecutionContext) -> None:
    """Grava o resultado dos modelos e testes em `metadata.testes_resultados`, como a linha de comando faz."""
    con = warehouse.connect(SETTINGS)
    try:
        with runs.track(con, stage, "dbt") as run:
            results = dbt_runner.read_results(SETTINGS, target=target)
            quality.record(con, run.id, results)
            run.rows_in = len(results)
            context.log.info(f"dbt {stage}: {len(results)} resultados de modelos e testes gravados")
            if stage == "transform_post":
                describe.raw(con, target)
                observability.notify(con, pipeline.freshness_limits())
    finally:
        con.close()


@dbt_assets(
    manifest=PROJECT.manifest_path,
    select="tag:pre_identity",
    name="dbt_pre_identity",
    dagster_dbt_translator=LayerTranslator(
        DagsterDbtTranslatorSettings(enable_duplicate_source_asset_keys=True)
    ),
)
def dbt_pre_identity(context: AssetExecutionContext, dbt: DbtCliResource) -> Iterator[Any]:
    """Fase 1 do dbt: os modelos de que a identidade precisa (`tag:pre_identity`)."""
    with step(context, "dbt antes da identidade"):
        invocation = dbt.cli(
            ["build", "--indirect-selection", "cautious"], context=context, target_path=DBT_TARGET
        )
        yield from invocation.stream()
    _record_dbt("transform_pre", invocation.target_path, context)


@multi_asset(
    specs=[AssetSpec(key=k, group_name="identity", deps=[IDS_MODEL]) for k in PEOPLE],
    name="identity",
)
def identity_asset(context: AssetExecutionContext) -> Iterator[MaterializeResult[Any]]:
    """Fase 2: resolve as pessoas de `int_pessoas_ids_vistos`; os modelos seguintes leem `identity.*`."""
    with step(context, "identidade"):
        created = build.resolve_identity(SETTINGS)
    context.log.info(f"identidade: {created} pessoas novas criadas")
    for key in PEOPLE:
        yield MaterializeResult(asset_key=key, metadata={"created": created})


@dbt_assets(
    manifest=PROJECT.manifest_path,
    exclude="tag:pre_identity",
    name="dbt_post_identity",
    dagster_dbt_translator=LayerTranslator(
        DagsterDbtTranslatorSettings(enable_duplicate_source_asset_keys=True)
    ),
)
def dbt_post_identity(context: AssetExecutionContext, dbt: DbtCliResource) -> Iterator[Any]:
    """Fase 3 do dbt: o resto dos modelos, que já leem `identity.pessoas` (todos menos `tag:pre_identity`)."""
    with step(context, "dbt depois da identidade"):
        invocation = dbt.cli(
            ["build", "--indirect-selection", "cautious"], context=context, target_path=DBT_TARGET
        )
        yield from invocation.stream()
    _record_dbt("transform_post", invocation.target_path, context)


@run_failure_sensor(name="falha_de_execucao", default_status=DefaultSensorStatus.RUNNING)
def failure_email(context: RunFailureSensorContext) -> None:
    """Avisa por e-mail quando qualquer execução falha (o e-mail da fase de marts só sai se ela chegar lá)."""
    run, base = context.dagster_run, os.environ.get("DADO_PUBLICO_DAGSTER_URL")
    steps = [e.step_key for e in context.get_step_failure_events() if e.step_key]
    url = f"{base.rstrip('/')}/runs/{run.run_id}" if base else None
    alert.notify_failure(run.job_name, run.run_id, steps, context.failure_event.message or "", url)


def _marts() -> list[AssetKey]:
    """Os modelos da camada marts, que o `export` grava no lake."""
    nodes = json.loads(PROJECT.manifest_path.read_text(encoding="utf-8"))["nodes"].values()
    return [
        AssetKey([n["schema"], n["name"]])
        for n in nodes
        if n["resource_type"] == "model" and n["fqn"][1] == "marts"
    ]


@asset(
    key=AssetKey(["publicacao", "lake"]),
    deps=_marts(),
    group_name="marts",
)
def export_asset(context: AssetExecutionContext) -> MaterializeResult[Any]:
    """Grava o lake público em Parquet (no R2, se houver segredo) depois dos testes do dbt (ADR 0035)."""
    with step(context, "export do lake"):
        result = dict(export.export(SETTINGS))
    context.log.info("export do lake: " + ", ".join(f"{k} {v:,}" for k, v in result.items()))
    return MaterializeResult(metadata=result)


@asset(
    key=AssetKey(["publicacao", "docs"]),
    deps=[AssetKey(["publicacao", "lake"])],
    group_name="marts",
)
def docs_asset(context: AssetExecutionContext) -> MaterializeResult[Any]:
    """Sobe ao R2 o dbt docs, o relatório do Elementary e a página inicial do lake (sem R2, não faz nada)."""
    with step(context, "publicação das docs"):
        pages = export.publish_docs(SETTINGS)
    context.log.info(f"docs: {len(pages)} páginas publicadas")
    return MaterializeResult(metadata={"paginas": len(pages)})


SCHEDULED = [s for s in SOURCES if s.schedule]
INGESTED = [key for s in SOURCES for key in _keys(s)]  # landing e raw de todas as fontes
jobs = [
    define_asset_job("atualizar_tudo", selection="*", tags=REFRESH),
    # captura tudo (landing e raw de todas as fontes), sem processar
    define_asset_job("capturar_tudo", selection=AssetSelection.assets(*INGESTED)),
    # só publica (lake no R2 e docs) o que já está pronto no warehouse, sem capturar nem transformar
    define_asset_job(
        "publicar",
        selection=AssetSelection.assets(AssetKey(["publicacao", "lake"]), AssetKey(["publicacao", "docs"])),
    ),
    # processa tudo (dbt, identidade, publicação) a partir do que já está no raw, sem capturar nada
    define_asset_job("processar_tudo", selection=AssetSelection.all() - AssetSelection.assets(*INGESTED)),
    *(
        define_asset_job(
            f"atualizar_{s.source}", selection=AssetSelection.assets(*_keys(s)).downstream(), tags=REFRESH
        )
        for s in SOURCES
    ),
    *(define_asset_job(f"captura_{s.source}", selection=AssetSelection.assets(*_keys(s))) for s in SOURCES),
]


def _latest(context: ScheduleEvaluationContext, key: AssetKey) -> float | None:
    event = context.instance.get_latest_materialization_event(key)
    return event.timestamp if event else None


def _request(context: ScheduleEvaluationContext, job: str) -> RunRequest | SkipReason:
    """Roda o job, salvo se já teve execução com SUCESSO (ou em andamento) hoje; falha ou nada: executa."""
    if pipeline.done_today(context.instance, job):
        return SkipReason(f"{job} já foi concluído (ou está em andamento) hoje")
    return RunRequest()


def _capture_schedule(source: contract.SourceContract) -> ScheduleDefinition:
    name = f"captura_{source.source}"

    @schedule(
        name=name,
        job_name=name,
        cron_schedule=str(source.schedule),
        execution_timezone=TIMEZONE,
        default_status=DefaultScheduleStatus.RUNNING,
    )
    def capture(context: ScheduleEvaluationContext) -> RunRequest | SkipReason:
        return _request(context, name)

    return capture


@schedule(
    name="processar_e_publicar",
    job_name="processar_tudo",
    cron_schedule=pipeline.CYCLE_CRON,
    execution_timezone=TIMEZONE,
    default_status=DefaultScheduleStatus.RUNNING,
)
def process_and_publish(context: ScheduleEvaluationContext) -> RunRequest | SkipReason:
    """Ciclo noturno: dbt, identidade, lake e docs, só se o raw recebeu dado desde o último ciclo completo."""
    raw = [_latest(context, k) for k in INGESTED if k.path[0] != "landing"]
    cycle = [_latest(context, k) for k in (*PEOPLE, AssetKey(["publicacao", "docs"]))]
    if not pipeline.needs_cycle(raw, cycle):
        return SkipReason("nenhum dado novo no raw desde o último ciclo completo")
    return _request(context, "processar_tudo")


schedules = [*(_capture_schedule(s) for s in SCHEDULED), process_and_publish]


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
        export_asset,
        docs_asset,
    ],
    asset_checks=freshness,
    jobs=jobs,
    sensors=sensors,
    schedules=schedules,
    # O DuckDB em arquivo aceita um escritor por vez: os passos rodam em sequência, num processo só.
    executor=in_process_executor,
    resources={"dbt": DbtCliResource(project_dir=PROJECT, profiles_dir=str(DBT_DIR))},
)
