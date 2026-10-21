"""Encadeia os dois motores: ingestão (extract, load) e transformação (dbt e identidade).

    extract (fonte -> landing) -> load (landing -> raw_<esfera>_<fonte>, dlt)
      -> transformação (dbt, identidade, dbt)

Cada etapa roda sozinha e pode rodar de novo. Se nada novo foi carregado, a transformação é pulada.
O Dagster (`definitions.py`) e a linha de comando chamam as mesmas funções.
"""

from dataclasses import dataclass
from datetime import UTC, datetime

from plataforma_dados.core import migrations
from plataforma_dados.core.settings import Settings
from plataforma_dados.ingestion import contract, fetch, landing, loader, monitoring
from plataforma_dados.transformation import build

SOURCE = "camara"


def contract_of(source: str = SOURCE) -> contract.SourceContract:
    return contract.find(source)


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
    items: list[landing.Item],
    rebuild: bool = False,
    force: bool = False,
    downloader: fetch.Downloader | None = None,
    head_request: fetch.HeadRequest | None = None,
) -> Summary:
    """Roda a cadeia inteira."""
    source = contract_of()
    summary = Summary()
    started = datetime.now(UTC)
    con = migrations.open_warehouse(settings)
    try:
        summary.items = landing.extract_plan(con, settings, source, items, downloader, head_request, force)
        summary.captures_loaded, summary.rows_loaded = loader.load_pending(con, settings, source, rebuild)
        summary.source_errors = monitoring.errors_since(con, started)
        built = build.is_built(con)
    finally:
        con.close()
    if summary.captures_loaded or rebuild or not built:
        summary.new_people = build.run(settings)
        summary.transformed = True
    return summary
