"""Roda o motor de transformação: dbt em duas fases, com a identidade de pessoas no meio.

    transform_pre (dbt: staging e intermediate que não dependem de identidade)
      -> identity (código próprio: chave de pessoa)
      -> transform_post (dbt: o resto do intermediate e os marts)

Os testes do dbt rodam junto com cada fase; teste com erro interrompe a execução. O resultado de
cada nó (modelo ou teste) é gravado em `metadata.testes_resultados`. Não importa a ingestão: parte
dos schemas `raw_*` e de `metadata.capturas`.
"""

from dado_publico_brasil.core import migrations, privado, runs, warehouse
from dado_publico_brasil.core.settings import Settings
from dado_publico_brasil.core.warehouse import Connection
from dado_publico_brasil.transformation import dbt, describe, identity, observability, snapshot
from dado_publico_brasil.transformation.quality import record

# `cautious`: um teste só roda quando todos os modelos de que depende já existem.
PRE_IDENTITY = ("--select", "tag:pre_identity", "--indirect-selection", "cautious")
POST_IDENTITY = ("--exclude", "tag:pre_identity", "--indirect-selection", "cautious")


class DbtFailure(RuntimeError):
    """Algum modelo ou teste do dbt falhou."""


def transform(settings: Settings, stage: str, *selection: str) -> None:
    """Roda `dbt build` (modelos e testes) para a seleção e registra o resultado.

    O chamador precisa ter fechado a sua conexão com o warehouse antes de chamar.
    """
    migrations.open_warehouse(
        settings
    ).close()  # o dbt lê `metadata.capturas`: o esquema precisa estar migrado
    print(f"== {stage}: dbt build iniciado", flush=True)
    started = runs.now()  # a execução mede o `dbt build` inteiro, não só a gravação dos resultados
    outcome = dbt.invoke(settings, "build", *selection, stream=True)
    con = warehouse.connect(settings)
    try:
        with runs.track(con, stage, "dbt", started=started) as run:
            record(con, run.id, outcome.results)
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


def run(settings: Settings) -> int:
    """Fase 1 do dbt, identidade e fase 2. Devolve quantas pessoas novas nasceram."""
    transform(settings, "transform_pre", *PRE_IDENTITY)
    created = resolve_identity(settings)
    transform(settings, "transform_post", *POST_IDENTITY)
    con = warehouse.connect(settings)
    try:
        privado.push_metadata(con, settings)
    finally:
        con.close()
    return created


def is_built(con: Connection) -> bool:
    """Os marts já existem neste warehouse?"""
    return "dim_pessoas" in warehouse.tables(con, "marts")
