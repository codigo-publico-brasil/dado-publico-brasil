"""Roda o motor de transformação: dbt em duas fases, com a identidade de pessoas no meio.

    transform_pre (dbt: staging e intermediate que não dependem de identidade)
      -> identity (código próprio: chave de pessoa)
      -> transform_post (dbt: o resto do intermediate e os marts)

Os testes do dbt rodam junto com cada fase; teste com erro interrompe a execução. O resultado de
cada nó (modelo, teste, frescor) é gravado em `metadata.dbt_results`. Não importa a ingestão: parte
dos schemas `raw_*` e de `metadata.captures`.
"""

from plataforma_dados.core import runs, warehouse
from plataforma_dados.core.settings import Settings
from plataforma_dados.core.warehouse import Connection
from plataforma_dados.transformation import dbt, identity, observability, snapshot
from plataforma_dados.transformation.quality import record

# `cautious`: um teste só roda quando todos os modelos de que depende já existem.
PRE_IDENTITY = ("--select", "tag:pre_identity", "--indirect-selection", "cautious")
POST_IDENTITY = ("--exclude", "tag:pre_identity", "--indirect-selection", "cautious")


class DbtFailure(RuntimeError):
    """Algum modelo ou teste do dbt falhou."""


def transform(settings: Settings, stage: str, *selection: str) -> None:
    """Roda `dbt build` (modelos e testes) para a seleção e registra o resultado.

    O chamador precisa ter fechado a sua conexão com o warehouse antes de chamar.
    """
    outcome = dbt.invoke(settings, "build", *selection)
    con = warehouse.connect(settings)
    try:
        with runs.track(con, stage, "dbt") as run:
            record(con, run.id, outcome.results)
            run.rows_in, run.rows_out = len(outcome.results), len(outcome.failures)
            if (
                stage == "transform_post"
            ):  # os marts estão prontos: fotografa e compara com a execução anterior
                observability.run(con, run.id)
            if outcome.returncode != 0:
                names = "; ".join(
                    f"{r['unique_id']}: {r['status']} {(r['message'] or '')[:1500]}" for r in outcome.failures
                )
                raise DbtFailure(names or outcome.output)
    finally:
        con.close()


def check_freshness(settings: Settings) -> None:
    """Roda `dbt source freshness` e registra o resultado (não interrompe a execução)."""
    outcome = dbt.invoke(settings, "source", "freshness", results_file="sources.json")
    con = warehouse.connect(settings)
    try:
        with runs.track(con, "freshness", "dbt") as run:
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
    """Fase 1 do dbt, frescor, identidade e fase 2. Devolve quantas pessoas novas nasceram."""
    transform(settings, "transform_pre", *PRE_IDENTITY)
    check_freshness(settings)
    created = resolve_identity(settings)
    transform(settings, "transform_post", *POST_IDENTITY)
    return created


def is_built(con: Connection) -> bool:
    """Os marts já existem neste warehouse?"""
    return "pessoas" in warehouse.tables(con, "marts")
