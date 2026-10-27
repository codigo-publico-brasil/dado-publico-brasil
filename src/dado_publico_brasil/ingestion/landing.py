"""Landing: os arquivos da fonte exatamente como chegaram, com hash, URL e data de captura.

O arquivo é guardado com o hash no nome e nunca é sobrescrito nem editado. Cada captura entra em
`metadata.captures`; capturar de novo o mesmo conteúdo só atualiza a data da última verificação.
Antes de baixar, pergunta-se à fonte se o arquivo mudou (`ETag`, `Last-Modified` e tamanho).

Três maneiras de montar o que baixar (o plano):
- explícito: os anos pedidos;
- histórico (massivo): todos os anos de um intervalo;
- incremental (a execução diária): os datasets completos e só a partição em curso (ano, mês ou legislatura)
  da fonte que declara `schedule`; sem `schedule`, só roda quando pedido.
"""

from collections.abc import Mapping
from contextlib import suppress
from datetime import UTC, date, datetime
from http.client import HTTPException
from pathlib import Path
from typing import Any

from dado_publico_brasil.core import runs
from dado_publico_brasil.core.settings import Settings
from dado_publico_brasil.core.warehouse import Connection, rows, scalar
from dado_publico_brasil.ingestion import fetch, monitoring
from dado_publico_brasil.ingestion.contract import Dataset, SourceContract
from dado_publico_brasil.ingestion.fetch import Downloader, HeadRequest

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


def folder(settings: Settings, source: str, dataset: str, partition: int | None, moment: str) -> Path:
    """Pasta de um arquivo no landing: `<fonte>/<dataset>/<partição ou "completo">/<AAAAMMDD da captura>`.

    A origem, a referência (ano, mês `AAAAMM` ou legislatura) e a data da extração aparecem no caminho."""
    reference = "completo" if partition is None else str(partition)
    return settings.landing_dir / source / dataset / reference / moment[:10].replace("-", "")


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


def partitions(dataset: Dataset, years: list[int] | set[int], today: date | None = None) -> list[int]:
    """Valores de partição de um dataset para os anos pedidos: os próprios anos ou suas legislaturas."""
    first = dataset.first_year
    valid = [
        y
        for y in years
        if (first is None or y >= first) and (first is None or (y - first) % dataset.step == 0)
    ]
    if dataset.partition == "legislature":
        return sorted({legislature_of(y) for y in valid})
    if dataset.partition == "month":
        now = today or datetime.now(UTC).date()
        months = (y * 100 + m for y in valid for m in range(1, 13))
        return sorted(v for v in months if (dataset.first_month or 0) <= v <= now.year * 100 + now.month)
    return sorted(valid)


def current_partition(dataset: Dataset, today: date) -> int:
    """A partição em curso: o ano, o mês (AAAAMM) ou a legislatura de hoje."""
    match dataset.partition:
        case "month":
            return today.year * 100 + today.month
        case "legislature":
            return legislature_of(today.year)
        case _:
            return today.year


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


def plan_incremental(contract: SourceContract, today: date | None = None) -> list[Item]:
    """Plano incremental (o da execução diária): só a partição em curso de cada dataset da fonte.

    Cada fonte diz, no seu YAML, quando se captura (`schedule`, um cron); sem `schedule` o plano é vazio e
    a fonte só roda quando pedida. Tudo que é retroativo (anos ou meses anteriores) exige pedir (`--years`
    ou `--historical`).
    """
    today = today or datetime.now(UTC).date()
    items: list[Item] = []
    if contract.schedule is None:
        return items
    for d in contract.datasets.values():
        if d.foreach:
            continue
        if not d.yearly:
            items.append((d.name, None))
        elif (current := current_partition(d, today)) in partitions(d, {today.year}):
            items.append((d.name, current))
    return items


# ---------------------------------------------------------------- lacunas e recuperação

RECOVERY_LIMIT = 3  # partições antigas por dataset e execução: pausa longa não vira carga gigante


def expected_partitions(dataset: Dataset, today: date) -> list[int]:
    """Todas as partições que a fonte deveria ter até hoje, de `first_year` (ou `first_month`) em diante."""
    if not dataset.yearly:
        return []
    first = dataset.first_year or (dataset.first_month // 100 if dataset.first_month else None)
    if first is None:
        return []
    return partitions(dataset, set(range(first, today.year + 1)), today)


def partition_gaps(
    con: Connection, contract: SourceContract, today: date | None = None
) -> dict[str, dict[str, Any]]:
    """Por dataset com partição: partições esperadas, capturadas, indisponíveis e faltantes.

    Indisponível é a partição que a fonte não publica (a última tentativa deu 404): não vira tentativa eterna
    e só é pedida de novo de forma explícita (`--years`). Faltante é o resto, falta nossa a recuperar."""
    today = today or datetime.now(UTC).date()
    result: dict[str, dict[str, Any]] = {}
    for d in contract.datasets.values():
        expected = expected_partitions(d, today)
        if d.foreach or not expected:
            continue
        got = {
            int(r["year"])
            for r in rows(
                con,
                "SELECT DISTINCT year FROM metadata.captures "
                "WHERE source = ? AND dataset = ? AND year IS NOT NULL",
                (contract.source, d.name),
            )
        }
        latest = rows(
            con,
            "SELECT partition, status, detail FROM metadata.source_checks WHERE source = ? AND dataset = ? "
            "AND check_name = 'availability' AND partition IS NOT NULL "
            "QUALIFY ROW_NUMBER() OVER (PARTITION BY partition ORDER BY id DESC) = 1",
            (contract.source, d.name),
        )
        unavailable = {
            int(r["partition"]) for r in latest if r["status"] == "error" and "404" in str(r["detail"])
        } - got
        missing = [p for p in expected if p not in got and p not in unavailable]
        result[d.name] = {
            "esperadas": len(expected),
            "capturadas": len(got & set(expected)),
            "indisponiveis": sorted(unavailable & set(expected)),
            "faltam": missing,
        }
    return result


def plan_recovery(
    con: Connection, contract: SourceContract, today: date | None = None, limit: int = RECOVERY_LIMIT
) -> list[Item]:
    """As partições passadas ainda não capturadas, as mais recentes primeiro, até `limit` por dataset.

    Só para fontes com `schedule`. A partição em curso fica com `plan_incremental` (o zip do mês corrente do
    DOU muda todo dia e não entra aqui)."""
    today = today or datetime.now(UTC).date()
    if contract.schedule is None:
        return []
    items: list[Item] = []
    for name, gap in partition_gaps(con, contract, today).items():
        current = current_partition(contract.datasets[name], today)
        items += [(name, p) for p in sorted(gap["faltam"], reverse=True) if p != current][:limit]
    return items


def record_gaps(con: Connection, contract: SourceContract) -> None:
    """Grava em `source_checks` (`particoes`) as partições de cada dataset: aviso se faltam, ok se não."""
    for name, gap in partition_gaps(con, contract).items():
        missing = gap["faltam"]
        detail = f"{gap['capturadas']} de {gap['esperadas']} partições"
        if gap["indisponiveis"]:
            detail += f"; a fonte não publica: {gap['indisponiveis']}"
        if missing:
            detail += f"; faltam: {missing}"
        monitoring.record(con, contract.source, name, None, "particoes", "warn" if missing else "ok", detail)


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
            file, digest, size = downloader(url, folder(settings, contract.source, dataset, year, runs.now()))
        except (OSError, HTTPException) as error:
            monitoring.record(con, contract.source, dataset, year, "availability", "error", str(error))
            return -1
        if previous is not None and previous["sha256"] == digest:  # mesmo conteúdo: fica o arquivo antigo
            if file != settings.storage_root / previous["path"]:
                file.unlink()
                with suppress(OSError):  # a pasta só some se ficou vazia
                    file.parent.rmdir()
            mark_checked(con, int(previous["id"]))
            run.rows_in = 1
            return int(previous["id"])
        monitoring.record(con, contract.source, dataset, year, "availability", "ok", f"{size} bytes")
        if not monitoring.check_integrity(
            con,
            contract.source,
            contract.datasets[dataset],
            year,
            file,
            url,
            headers.get("size"),
            contract.format_of(dataset),
        ):
            return -1  # o arquivo fica no landing como evidência, mas não vira captura (tenta de novo)
        if contract.datasets[dataset].raw:
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
    recover: bool = False,
) -> int:
    """Executa um plano, item a item. Devolve quantos itens foram processados.

    Com `recover` (a execução incremental), soma ao plano as partições passadas que faltam (`plan_recovery`).
    Ao fim, registra por dataset o estado das partições (`particoes` em `source_checks`)."""
    if recover:
        items = [*items, *plan_recovery(con, contract)]
    for dataset, year in items:
        print(f"Extraindo {dataset} {year or ''}".strip(), flush=True)
        extract(con, settings, contract, dataset, year, downloader, head_request, force)
    record_gaps(con, contract)
    return len(items)
