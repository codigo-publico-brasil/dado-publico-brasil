"""Roda o motor de transformação: dbt em duas fases, com a identidade de pessoas no meio.

    transform_pre (dbt: staging e intermediate que não dependem de identidade)
      -> identity (código próprio: chave de pessoa)
      -> transform_post (dbt: o resto do intermediate e os marts)

Cada fase só constrói os modelos com entrada nova (`selection`, ADR 0047); sem estado, com outro código e
aos domingos, constrói todos. Os testes do dbt rodam junto com cada fase; teste com erro interrompe a
execução. O resultado de cada nó (modelo ou teste) é gravado em `metadata.testes_resultados`. Não importa a
ingestão: parte dos schemas `raw_*` e de `metadata.capturas`.
"""

from dado_publico_brasil.core import migrations, privado, runs, warehouse
from dado_publico_brasil.core.settings import Settings
from dado_publico_brasil.core.warehouse import Connection
from dado_publico_brasil.transformation import (
    dbt,
    describe,
    identity,
    observability,
    selection,
    snapshot,
)
from dado_publico_brasil.transformation.quality import record

PRE_IDENTITY = selection.FULL_ARGS["transform_pre"]
POST_IDENTITY = selection.FULL_ARGS["transform_post"]


class DbtFailure(RuntimeError):
    """Algum modelo ou teste do dbt falhou."""


def transform(settings: Settings, stage: str, *args: str, plan: selection.Plan | None = None) -> None:
    """Roda `dbt build` (modelos e testes) para a seleção (`args`, ou a do `plan`) e registra o resultado.

    Um `plan` sem nada a construir não chama o dbt. O chamador precisa ter fechado a sua conexão com o
    warehouse antes de chamar.
    """
    migrations.open_warehouse(
        settings
    ).close()  # o dbt lê `metadata.capturas`: o esquema precisa estar migrado
    started = runs.now()  # a execução mede o `dbt build` inteiro, não só a gravação dos resultados
    if plan:
        print(f"== {stage}: {'completo' if plan.full else 'seletivo'} ({plan.reason})", flush=True)
    if plan and plan.skip:
        outcome = dbt.Outcome(0, "", [])
    else:
        print(f"== {stage}: dbt build iniciado", flush=True)
        outcome = dbt.invoke(settings, "build", *(plan.args if plan else args), stream=True)
    con = warehouse.connect(settings)
    try:
        with runs.track(con, stage, "dbt", started=started) as run:
            record(con, run.id, outcome.results)
            run.completa = bool(plan and plan.completed(outcome.results))
            run.rows_in, run.rows_out = len(outcome.results), len(outcome.failures)
            if (
                stage == "transform_post"
            ):  # os marts estão prontos: descreve o raw e avisa se algo está errado
                describe.raw(con, dbt.target_dir(settings))
                observability.notify(con)
            if outcome.returncode != 0:
                names = "; ".join(
                    f"{r['unique_id']}: {r['status']} {(r['message'] or '')[:1500]}" for r in outcome.failures
                )
                raise DbtFailure(names or outcome.output)
    finally:
        con.close()


def check_freshness(settings: Settings) -> None:
    """Roda `dbt source freshness` e registra o resultado (não interrompe a execução)."""
    started = runs.now()
    outcome = dbt.invoke(settings, "source", "freshness", results_file="sources.json")
    con = warehouse.connect(settings)
    try:
        with runs.track(con, "freshness", "dbt", started=started) as run:
            record(con, run.id, outcome.results)
            run.rows_in = len(outcome.results)
    finally:
        con.close()


def resolve_identity(settings: Settings) -> int:
    """Cria as pessoas novas e guarda a cópia imutável da identidade. Devolve quantas foram criadas."""
    con = warehouse.connect(settings)
    try:
        created = identity.resolve(con)[1]
        snapshot.take(con, settings)
        return created
    finally:
        con.close()


def phase(settings: Settings, stage: str, full: bool = False) -> None:
    """Escolhe os modelos da fase (`selection.plan`) e os constrói; `full` refaz todos."""
    con = migrations.open_warehouse(settings)
    try:
        plan = selection.plan(con, settings, stage, force=full)
    finally:
        con.close()
    transform(settings, stage, plan=plan)


def run(settings: Settings, full: bool = False) -> int:
    """Fase 1 do dbt, identidade e fase 2. Devolve quantas pessoas novas nasceram.

    `full` refaz todos os modelos (a seleção só pula o que não tem entrada nova)."""
    phase(settings, "transform_pre", full)
    created = resolve_identity(settings)
    phase(settings, "transform_post", full)
    con = warehouse.connect(settings)
    try:
        privado.push_metadata(con, settings)
    finally:
        con.close()
    return created


def is_built(con: Connection) -> bool:
    """Os marts já existem neste warehouse?"""
    return "dim_pessoas" in warehouse.tables(con, "marts")
