"""Encadeia os dois motores: ingestão (extract, load) e transformação (dbt e identidade).

    para cada fonte de `sources/`: extract (fonte -> landing) -> load (landing -> raw_<esfera>_<fonte>, dlt)
    depois, uma vez: transformação (dbt, identidade, dbt)

Cada etapa roda sozinha e pode rodar de novo. Se nada novo foi carregado, a transformação é pulada.
O Dagster (`definitions.py`) e a linha de comando chamam as mesmas funções.
"""

import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from zoneinfo import ZoneInfo

from dagster import DagsterRunStatus, RunsFilter

from dado_publico_brasil.core import migrations, runs
from dado_publico_brasil.core.settings import Settings
from dado_publico_brasil.ingestion import contract, fetch, foreach, landing, loader, monitoring
from dado_publico_brasil.transformation import build

Plan = Callable[[contract.SourceContract], list[landing.Item]]


@contextmanager
def step(context: Any, name: str) -> Iterator[None]:
    """Registra no log do Dagster (`context.log`, aba Runs) início, fim e duração de um passo, e a falha."""
    context.log.info(f"{name}: iniciando")
    started = time.monotonic()
    try:
        yield
    except Exception:
        context.log.error(f"{name}: falhou após {time.monotonic() - started:,.0f}s")
        raise
    context.log.info(f"{name}: concluído em {time.monotonic() - started:,.0f}s")


@dataclass
class Summary:
    items: int = 0
    captures_loaded: int = 0
    rows_loaded: int = 0
    source_errors: int = 0  # verificações das fontes com erro nesta execução (metadata.fontes_verificacoes)
    new_people: int = 0
    transformed: bool = False


def run_all(
    settings: Settings,
    plan: Plan,
    rebuild: bool = False,
    force: bool = False,
    downloader: fetch.Downloader | None = None,
    head_request: fetch.HeadRequest | None = None,
    only: str | None = None,
    per_item: int | None = None,
    get: foreach.Get | None = None,
    dataset_name: str | None = None,
) -> Summary:
    """Roda a cadeia inteira para todas as fontes (ou só `only`). `plan` diz o que extrair de cada uma.

    Os datasets por item (`foreach`) só rodam com `per_item`: quantos itens por dataset, os mais recentes
    primeiro.
    """
    summary = Summary()
    started = datetime.now(UTC)
    con = migrations.open_warehouse(settings)
    try:
        for source in contract.find_all():
            if only in (None, source.source):
                summary.items += landing.extract_plan(
                    con, settings, source, plan(source), downloader, head_request, force
                )
                captures, rows = loader.load_pending(con, settings, source, rebuild)
                if per_item:
                    for name, dataset in source.datasets.items():
                        if dataset.foreach and dataset_name in (None, name):
                            summary.items += foreach.capture(con, settings, source, name, per_item, get)
                            # carrega já: o próximo dataset por item pode listar os itens deste
                            more_captures, more_rows = loader.load_pending(con, settings, source)
                            captures, rows = captures + more_captures, rows + more_rows
                summary.captures_loaded += captures
                summary.rows_loaded += rows
        summary.source_errors = monitoring.errors_since(con, started)
        built = build.is_built(con)
    finally:
        con.close()
    if summary.captures_loaded or rebuild or not built:
        summary.new_people = build.run(settings, full=rebuild)
        summary.transformed = True
    return summary


def ensure_raw(settings: Settings, log: loader.Log = loader.default_log) -> None:
    """Garante a tabela do raw (vazia, se preciso) de todo dataset `raw: true` de todas as fontes."""
    con = migrations.open_warehouse(settings)
    try:
        for source in contract.find_all():
            loader.ensure_tables(settings, source, con, log)
    finally:
        con.close()


REFRESH_TAG = (
    "dado_publico/refazer"  # tag dos jobs `atualizar_*`: refazem o que depende do raw mesmo sem dado novo
)


def freshness_limits() -> dict[tuple[str, str], int]:
    """A idade máxima da última verificação de cada (fonte, dataset) com `max_age_days` no contrato."""
    return {
        (spec.source, name): dataset.max_age_days
        for spec in contract.find_all()
        for name, dataset in spec.datasets.items()
        if dataset.max_age_days is not None
    }


def registers_update(captures: int, refresh: bool, never_registered: bool) -> bool:
    """O raw registra atualização (libera o que vem depois) com captura nova, ao refazer ou na 1ª vez."""
    return bool(captures) or refresh or never_registered


# Ciclo noturno (ADR 0042): roda o job `processar_tudo` (dbt, identidade, lake e docs) uma vez por noite,
# depois das capturas (01:00 a 02:20, fuso America/Sao_Paulo). Se uma captura ainda estiver na fila, o ciclo
# espera: a fila é uma execução por vez. A publicação é o último passo.
CYCLE_CRON = "0 4 * * *"


def needs_cycle(raw: list[float | None], cycle: list[float | None]) -> bool:
    """Roda o ciclo se o raw recebeu dado depois do passo mais antigo do último ciclo (ou se nunca fechou).

    `raw`: instante da última atualização de cada tabela do raw; `cycle`: o da última materialização de um
    ativo de saída do ciclo (identidade e docs). `None` = nunca. Só lê o log de eventos do Dagster.
    """
    if any(t is None for t in cycle):
        return True
    arrived = [t for t in raw if t is not None]
    return bool(arrived) and max(arrived) > min(t for t in cycle if t is not None)


TIMEZONE = runs.TIMEZONE  # fuso dos agendamentos e do "dia" de cada um


DONE_OR_RUNNING = [
    DagsterRunStatus.SUCCESS,
    DagsterRunStatus.QUEUED,
    DagsterRunStatus.NOT_STARTED,
    DagsterRunStatus.STARTING,
    DagsterRunStatus.STARTED,
]


def done_today(instance: Any, job: str, now: datetime | None = None) -> bool:
    """O job já teve execução concluída com SUCESSO ou ainda em andamento (ou na fila) desde 00:00 local?

    Só lê o armazenamento do Dagster. Falha ou cancelamento não contam: o agendamento tenta de novo (ou o
    fundador relança). A fila conta: tiques perdidos, recuperados em sequência, não enfileiram N vezes.
    """
    local = (now or datetime.now(UTC)).astimezone(ZoneInfo(TIMEZONE))
    midnight = local.replace(hour=0, minute=0, second=0, microsecond=0)
    # o Dagster ignora o fuso de um datetime que não seja UTC: converte antes
    found = RunsFilter(job_name=job, statuses=DONE_OR_RUNNING, created_after=midnight.astimezone(UTC))
    return bool(instance.get_runs(filters=found, limit=1))
