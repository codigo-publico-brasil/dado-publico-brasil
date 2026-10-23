"""Landing: os arquivos da fonte exatamente como chegaram, com hash, URL e data de captura.

O arquivo é guardado com o hash no nome e nunca é sobrescrito nem editado. Cada captura entra em
`metadata.captures`; capturar de novo o mesmo conteúdo só atualiza a data da última verificação.
Antes de baixar, pergunta-se à fonte se o arquivo mudou (`ETag`, `Last-Modified` e tamanho).

Três maneiras de montar o que baixar (o plano):
- explícito: os anos pedidos;
- histórico (massivo): todos os anos de um intervalo;
- incremental: os datasets completos e só os anos que ainda podem mudar (por padrão o corrente e
  o anterior).
"""

from collections.abc import Mapping
from datetime import UTC, datetime
from http.client import HTTPException
from typing import Any

from plataforma_dados.core import runs
from plataforma_dados.core.settings import Settings
from plataforma_dados.core.warehouse import Connection, rows, scalar
from plataforma_dados.ingestion import fetch, monitoring
from plataforma_dados.ingestion.contract import Dataset, SourceContract
from plataforma_dados.ingestion.fetch import Downloader, HeadRequest

Item = tuple[str, int | None]


def unchanged(previous: Mapping[str, Any] | None, headers: Mapping[str, str | None]) -> bool:
    """Verdadeiro só se a fonte informa o mesmo `ETag`, ou o mesmo `Last-Modified` e tamanho."""
    if previous is None:
        return False
    if headers.get("etag") and headers["etag"] == previous["etag"]:
        return True
    return bool(
        headers.get("last_modified")
        and headers["last_modified"] == previous["last_modified"]
        and headers.get("size")
        and str(previous["size_bytes"]) == headers["size"]
    )


def last_capture(con: Connection, url: str) -> dict[str, Any] | None:
    found = rows(con, "SELECT * FROM metadata.captures WHERE url = ? ORDER BY id DESC LIMIT 1", (url,))
    return found[0] if found else None


def register_capture(
    con: Connection,
    source: str,
    dataset: str,
    year: int | None,
    url: str,
    sha256: str,
    size_bytes: int,
    path: str,
    run_id: int,
    headers: Mapping[str, str | None] | None = None,
) -> int:
    """Anota a captura. O mesmo conteúdo (URL e hash) não é duplicado."""
    moment = runs.now()
    h = headers or {}
    con.execute(
        "INSERT INTO metadata.captures (source, dataset, year, url, sha256, size_bytes, path, "
        "captured_at, last_checked_at, run_id, etag, last_modified) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
        "ON CONFLICT (url, sha256) DO UPDATE SET last_checked_at = excluded.last_checked_at, "
        "etag = excluded.etag, last_modified = excluded.last_modified",
        (source, dataset, year, url, sha256, size_bytes, path, moment, moment, run_id)
        + (h.get("etag"), h.get("last_modified")),
    )
    return int(scalar(con, "SELECT id FROM metadata.captures WHERE url = ? AND sha256 = ?", (url, sha256)))


def mark_checked(con: Connection, capture_id: int) -> None:
    con.execute("UPDATE metadata.captures SET last_checked_at = ? WHERE id = ?", (runs.now(), capture_id))


def current_captures(con: Connection, source: str) -> list[dict[str, Any]]:
    """A captura mais recente de cada URL da fonte (o que o loader deve ler)."""
    return rows(
        con,
        "SELECT * FROM metadata.captures c WHERE c.source = ? "
        "AND c.id = (SELECT MAX(id) FROM metadata.captures WHERE url = c.url) "
        "ORDER BY c.dataset, c.year, c.id",
        (source,),
    )


# ---------------------------------------------------------------- planos


def current_year() -> int:
    return datetime.now(UTC).year


def legislature_of(year: int) -> int:
    """Número da legislatura em curso no ano (a 56ª começou em 2019; cada uma dura quatro anos)."""
    return 56 + (year - 2019) // 4


def partitions(dataset: Dataset, years: list[int] | set[int]) -> list[int]:
    """Valores de partição de um dataset para os anos pedidos: os próprios anos ou suas legislaturas."""
    first = dataset.first_year
    valid = [
        y
        for y in years
        if (first is None or y >= first) and (first is None or (y - first) % dataset.step == 0)
    ]
    if dataset.partition == "legislature":
        return sorted({legislature_of(y) for y in valid})
    return sorted(valid)


def mutable_years(dataset: Dataset, current: int) -> list[int]:
    """Anos que ainda podem mudar: do corrente até `stable_after_years` anos atrás."""
    return list(range(current - dataset.stable_after_years, current + 1))


def plan(contract: SourceContract, years: list[int], extra_years: list[int] | None = None) -> list[Item]:
    """Plano explícito: datasets completos e os anos pedidos dos anuais.

    `extra_years` vale só para datasets com `extra_years: true` (por exemplo, proposições).
    """
    items: list[Item] = []
    for d in contract.datasets.values():
        if d.foreach:
            continue  # por item: só com --foreach (ver foreach.py)
        if not d.yearly:
            items.append((d.name, None))
            continue
        wanted = set(years) | (set(extra_years or ()) if d.extra_years else set())
        items += [(d.name, v) for v in partitions(d, wanted)]
    return items


def plan_historical(
    contract: SourceContract,
    start: int,
    end: int | None = None,
    extra_years: list[int] | None = None,
) -> list[Item]:
    """Plano massivo: todos os anos de `start` até `end` (padrão: o ano corrente)."""
    return plan(contract, list(range(start, (end or current_year()) + 1)), extra_years)


def plan_incremental(contract: SourceContract, current: int | None = None) -> list[Item]:
    """Plano incremental: datasets completos e só os anos que ainda podem mudar."""
    current = current or current_year()
    items: list[Item] = []
    for d in contract.datasets.values():
        if d.foreach:
            continue
        if not d.yearly:
            items.append((d.name, None))
        else:
            items += [(d.name, v) for v in partitions(d, mutable_years(d, current))]
    return items


# ---------------------------------------------------------------- extração


def extract(
    con: Connection,
    settings: Settings,
    contract: SourceContract,
    dataset: str,
    year: int | None = None,
    downloader: Downloader | None = None,
    head_request: HeadRequest | None = None,
    force: bool = False,
) -> int:
    """Captura um dataset e devolve o id da captura (nova ou a anterior, se nada mudou).

    O arquivo vai para `<storage_root>/landing/<fonte>/`. `force` ignora a pergunta à fonte. Se a fonte
    falhar, a falha é registrada em `metadata.source_checks` e devolve -1, sem interromper o plano.
    """
    url = contract.url(dataset, year)
    downloader = downloader or fetch.downloader(contract, dataset)
    head_request = head_request or fetch.head_request(contract, dataset)
    with runs.track(con, "extract", contract.source, dataset, year) as run:
        previous = last_capture(con, url)
        try:
            headers = {} if force else head_request(url)
        except OSError:
            headers = {}
        if not force and previous is not None and unchanged(previous, headers):
            mark_checked(con, int(previous["id"]))
            run.rows_in = 1
            return int(previous["id"])
        try:
            file, digest, size = downloader(url, settings.landing_dir / contract.source)
        except (OSError, HTTPException) as error:
            monitoring.record(con, contract.source, dataset, year, "availability", "error", str(error))
            return -1
        monitoring.record(con, contract.source, dataset, year, "availability", "ok", f"{size} bytes")
        monitoring.check_header(con, contract, contract.datasets[dataset], year, file)
        run.rows_in = run.rows_out = 1
        relative = file.relative_to(settings.storage_root).as_posix()
        return register_capture(
            con, contract.source, dataset, year, url, digest, size, relative, run.id, headers
        )


def extract_plan(
    con: Connection,
    settings: Settings,
    contract: SourceContract,
    items: list[Item],
    downloader: Downloader | None = None,
    head_request: HeadRequest | None = None,
    force: bool = False,
) -> int:
    """Executa um plano, item a item. Devolve quantos itens foram processados."""
    for dataset, year in items:
        print(f"Extraindo {dataset} {year or ''}".strip(), flush=True)
        extract(con, settings, contract, dataset, year, downloader, head_request, force)
    return len(items)
