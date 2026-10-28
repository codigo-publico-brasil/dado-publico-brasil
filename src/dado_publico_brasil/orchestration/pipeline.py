"""Encadeia os dois motores: ingestão (extract, load) e transformação (dbt e identidade).

    para cada fonte de `sources/`: extract (fonte -> landing) -> load (landing -> raw_<esfera>_<fonte>, dlt)
    depois, uma vez: transformação (dbt, identidade, dbt)

Cada etapa roda sozinha e pode rodar de novo. Se nada novo foi carregado, a transformação é pulada.
O Dagster (`definitions.py`) e a linha de comando chamam as mesmas funções.
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from dado_publico_brasil.core import migrations
from dado_publico_brasil.core.settings import Settings
from dado_publico_brasil.ingestion import contract, fetch, foreach, landing, loader, monitoring
from dado_publico_brasil.transformation import build

Plan = Callable[[contract.SourceContract], list[landing.Item]]


@dataclass
class Summary:
    items: int = 0
    captures_loaded: int = 0
    rows_loaded: int = 0
    source_errors: int = 0  # verificações das fontes com erro nesta execução (metadata.source_checks)
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
        summary.new_people = build.run(settings)
        summary.transformed = True
    return summary


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
