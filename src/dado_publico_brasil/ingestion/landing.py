"""Landing: os arquivos da fonte exatamente como chegaram, com hash, URL e data de captura.

O arquivo é guardado com o hash no nome e nunca é sobrescrito nem editado. Cada captura entra em
`metadata.capturas`; capturar de novo o mesmo conteúdo só atualiza a data da última verificação.
Antes de baixar, pergunta-se à fonte se o arquivo mudou (`ETag`, `Last-Modified` e tamanho).

Três maneiras de montar o que baixar (o plano):
- explícito: os anos pedidos;
- histórico (massivo): todos os anos de um intervalo;
- incremental (a execução diária): os datasets completos e só a partição em curso (ano, mês ou legislatura)
  da fonte que declara `schedule`; sem `schedule`, só roda quando pedido.
"""

import hashlib
import json
import logging
import shutil
import urllib.error
from collections.abc import Mapping
from contextlib import suppress
from datetime import date, datetime, timedelta
from http.client import HTTPException
from pathlib import Path
from typing import Any

from dado_publico_brasil.core import privado, runs
from dado_publico_brasil.core.settings import Settings
from dado_publico_brasil.core.warehouse import Connection, rows, scalar
from dado_publico_brasil.ingestion import arquivos, fetch, monitoring
from dado_publico_brasil.ingestion.contract import Dataset, SourceContract
from dado_publico_brasil.ingestion.fetch import Downloader, HeadRequest

logger = logging.getLogger(__name__)

Item = tuple[str, int | None]


def unchanged(previous: Mapping[str, Any] | None, headers: Mapping[str, str | None]) -> bool:
    """Verdadeiro só se a fonte informa o mesmo `ETag`, ou o mesmo `Last-Modified` e tamanho."""
    if previous is None:
        return False
    if headers.get("etag") and headers["etag"] == previous["etag"]:
        return True
    return bool(
        headers.get("last_modified")
        and headers["last_modified"] == previous["ultima_modificacao"]
        and headers.get("size")
        and str(previous["qtd_bytes"]) == headers["size"]
    )


def folder(settings: Settings, source: str, dataset: str, partition: int | None, moment: str) -> Path:
    """Pasta de um arquivo no landing: `<fonte>/<dataset>/<partição ou "completo">/<AAAAMMDD da captura>`.

    A origem, a referência (ano, mês `AAAAMM` ou legislatura) e a data da extração aparecem no caminho."""
    reference = "completo" if partition is None else str(partition)
    return settings.landing_dir / source / dataset / reference / moment[:10].replace("-", "")


def last_capture(con: Connection, url: str) -> dict[str, Any] | None:
    found = rows(
        con, "SELECT * FROM metadata.capturas WHERE url = ? ORDER BY id_captura DESC LIMIT 1", (url,)
    )
    return found[0] if found else None


def same_file(
    con: Connection,
    contract: SourceContract,
    dataset: str,
    url: str,
    year: int | None,
    storage_root: Path,
    headers: Mapping[str, str | None],
) -> dict[str, Any] | None:
    """Captura de outro dataset do mesmo arquivo (URL igual até o `#`) que a fonte diz não ter mudado.

    Vários datasets leem o mesmo pacote (emendas, contratos): baixa-se uma vez, os demais reaproveitam."""
    base = url.partition("#")[0]
    found = rows(
        con,
        "SELECT * FROM metadata.capturas WHERE fonte = ? AND dataset <> ? "
        "AND particao IS NOT DISTINCT FROM ? "
        "AND (url = ? OR url LIKE ?) ORDER BY id_captura DESC LIMIT 1",
        (contract.source, dataset, year, base, base + "#%"),
    )
    if found and (storage_root / found[0]["caminho"]).exists() and unchanged(found[0], headers):
        return found[0]
    return None


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
    """Anota a captura. O mesmo conteúdo da captura vigente da URL não é duplicado; a volta a um conteúdo
    antigo (A, B, A) é captura nova, para o vigente e o histórico seguirem a fonte."""
    moment = runs.now()
    h = headers or {}
    last = last_capture(con, url)
    if last and last["sha256"] == sha256:
        con.execute(
            "UPDATE metadata.capturas SET dt_verificacao = ?, etag = ?, ultima_modificacao = ? "
            "WHERE id_captura = ?",
            (moment, h.get("etag"), h.get("last_modified"), last["id_captura"]),
        )
        return int(last["id_captura"])
    return int(
        scalar(
            con,
            "INSERT INTO metadata.capturas (fonte, dataset, particao, url, sha256, qtd_bytes, caminho, "
            "dt_captura, dt_verificacao, id_execucao, etag, ultima_modificacao) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) RETURNING id_captura",
            (source, dataset, year, url, sha256, size_bytes, path, moment, moment, run_id)
            + (h.get("etag"), h.get("last_modified")),
        )
    )


def mark_checked(con: Connection, capture_id: int) -> None:
    con.execute(
        "UPDATE metadata.capturas SET dt_verificacao = ? WHERE id_captura = ?", (runs.now(), capture_id)
    )


def current_captures(con: Connection, source: str) -> list[dict[str, Any]]:
    """A captura mais recente de cada URL da fonte (o que o loader deve ler)."""
    return rows(
        con,
        "SELECT * FROM metadata.capturas c WHERE c.fonte = ? "
        "AND c.id_captura = (SELECT MAX(id_captura) FROM metadata.capturas WHERE url = c.url) "
        "ORDER BY c.dataset, c.particao, c.id_captura",
        (source,),
    )


def content_version(con: Connection, source: str) -> str:
    """Impressão digital do conteúdo vigente da fonte: só muda quando uma captura traz arquivo novo."""
    pairs = sorted((c["url"], c["sha256"]) for c in current_captures(con, source))
    return hashlib.sha256(json.dumps(pairs).encode()).hexdigest()


# ---------------------------------------------------------------- planos


def current_year() -> int:
    return runs.today().year


def sequence_of(dataset: Dataset, year: int) -> int:
    """Valor da partição `sequence` no ano: `first_value + (ano - first_year) // years`."""
    first_year, first_value, years = dataset.sequence  # type: ignore[misc]
    return first_value + (year - first_year) // years


def partitions(dataset: Dataset, years: list[int] | set[int], today: date | None = None) -> list[int]:
    """Valores de partição de um dataset para os anos pedidos: os anos, os meses ou a sequência."""
    first = dataset.first_year
    valid = [
        y
        for y in years
        if (first is None or y >= first) and (first is None or (y - first) % dataset.step == 0)
    ]
    if dataset.partition == "sequence":
        return sorted({sequence_of(dataset, y) for y in valid})
    if dataset.partition == "day":
        start, end = _day(dataset.first_day or 0), _day(current_partition(dataset, today or runs.today()))
        days = (_number(start + timedelta(n)) for n in range((end - start).days + 1))
        return [v for v in days if v // 10000 in valid]
    if dataset.partition == "month":
        last = current_partition(dataset, today or runs.today())
        months = (y * 100 + m for y in valid for m in range(1, 13))
        return sorted(v for v in months if (dataset.first_month or 0) <= v <= last)
    return sorted(valid)


def _day(value: int) -> date:
    return datetime.strptime(str(value), "%Y%m%d").date()


def _number(day: date) -> int:
    return day.year * 10000 + day.month * 100 + day.day


def current_partition(dataset: Dataset, today: date) -> int:
    """A partição em curso: o ano, o mês (AAAAMM), o dia (AAAAMMDD) ou o valor da sequência de hoje.

    Com `lag_months` (ou `lag_days`), é a última que a fonte já deveria ter publicado."""
    match dataset.partition:
        case "day":
            return _number(today - timedelta(dataset.lag_days))
        case "month":
            month = today.year * 100 + today.month
            for _ in range(dataset.lag_months):
                month = previous_month(month)
            return month
        case "sequence":
            return sequence_of(dataset, today.year)
        case _:
            return today.year


def previous_month(value: int) -> int:
    """O mês (AAAAMM) anterior."""
    return value - 1 if value % 100 > 1 else (value // 100 - 1) * 100 + 12


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
    """Plano incremental (o da execução diária): a partição em curso de cada dataset (e o mês anterior).

    Cada fonte diz, no seu YAML, quando se captura (`schedule`, um cron); sem `schedule` o plano é vazio e
    a fonte só roda quando pedida. Tudo que é retroativo (anos ou meses anteriores) exige pedir (`--years`
    ou `--historical`). Dataset `on_demand` fica fora: só vem quando pedido.
    """
    today = today or runs.today()
    items: list[Item] = []
    if contract.schedule is None:
        return items
    for d in contract.datasets.values():
        if d.foreach or d.on_demand:
            continue
        if not d.yearly:
            items.append((d.name, None))
        else:
            valid = partitions(d, {today.year - 1, today.year}, today)
            current = current_partition(d, today)
            # mês anterior: fechado e sem mudança custa um HEAD; a virada não perde o fim dele
            wanted = (current, previous_month(current)) if d.partition == "month" else (current,)
            items += [(d.name, p) for p in sorted(wanted) if p in valid]
    return items


# ---------------------------------------------------------------- lacunas e recuperação

RECOVERY_LIMIT = 3  # partições antigas por dataset e execução: pausa longa não vira carga gigante


def expected_partitions(dataset: Dataset, today: date) -> list[int]:
    """Todas as partições que a fonte deveria ter até hoje, de `first_year` (ou `first_month`) em diante."""
    if not dataset.yearly:
        return []
    first = dataset.first_year or (
        (dataset.first_month or dataset.first_day or 0) // (10000 if dataset.first_day else 100) or None
    )
    if first is None:
        return []
    return partitions(dataset, set(range(first, today.year + 1)), today)


def partition_gaps(
    con: Connection, contract: SourceContract, today: date | None = None
) -> dict[str, dict[str, Any]]:
    """Por dataset com partição: partições esperadas, capturadas, indisponíveis e faltantes.

    Indisponível é a partição que a fonte não publica (a última tentativa deu 404): não vira tentativa eterna
    e só é pedida de novo de forma explícita (`--years`). Faltante é o resto, falta nossa a recuperar."""
    today = today or runs.today()
    result: dict[str, dict[str, Any]] = {}
    for d in contract.datasets.values():
        expected = expected_partitions(d, today)
        if d.foreach or not expected:
            continue
        got = {
            int(r["particao"])
            for r in rows(
                con,
                "SELECT DISTINCT particao FROM metadata.capturas "
                "WHERE fonte = ? AND dataset = ? AND particao IS NOT NULL",
                (contract.source, d.name),
            )
        }
        latest = rows(
            con,
            "SELECT particao, resultado, tipo_ocorrencia FROM metadata.fontes_verificacoes WHERE fonte = ? "
            "AND "
            "dataset = ? "
            "AND verificacao = 'availability' AND particao IS NOT NULL "
            "QUALIFY ROW_NUMBER() OVER (PARTITION BY particao ORDER BY id_verificacao DESC) = 1",
            (contract.source, d.name),
        )
        errors = {int(r["particao"]): r["tipo_ocorrencia"] for r in latest if r["resultado"] == "error"}
        # com `missing_status`, nao_publicado é falta a retomar (o arquivo pode sair), não indisponível
        gone = ("nao_encontrado",) if d.missing_status else ("nao_encontrado", "nao_publicado")
        unavailable = {p for p, kind in errors.items() if kind in gone} - got
        waiting = {p for p, kind in errors.items() if kind == "nao_publicado" and d.missing_status} - got
        current = current_partition(d, today)  # o anterior ainda é pedido: um 404 na virada não o descarta
        if d.partition == "month":
            unavailable.discard(previous_month(current))
        elif d.partition == "day":
            unavailable -= {
                current,
                _number(_day(current) - timedelta(1)),
            }  # o dia mais recente é o `nao_publicado`
        missing = [p for p in expected if p not in got and p not in unavailable and not d.on_demand]
        result[d.name] = {
            "esperadas": len(expected),
            "capturadas": len(got & set(expected)),
            "indisponiveis": sorted(unavailable & set(expected)),
            "faltam": missing,  # `on_demand`: sempre vazio, o que falta é escolha e não lacuna
            "sob_demanda": d.on_demand,
        }
        if d.missing_status:  # faltam e a última tentativa foi nao_publicado
            result[d.name]["aguardando"] = sorted(waiting & set(missing))
    return result


def plan_recovery(
    con: Connection, contract: SourceContract, today: date | None = None, limit: int = RECOVERY_LIMIT
) -> list[Item]:
    """As partições passadas ainda não capturadas, as mais recentes primeiro, até `limit` por dataset.

    Só para fontes com `schedule`. A partição em curso fica com `plan_incremental`
    (o pacote do mês corrente muda todo dia e não entra aqui)."""
    today = today or runs.today()
    if contract.schedule is None:
        return []
    items: list[Item] = []
    for name, gap in partition_gaps(con, contract, today).items():
        current = current_partition(contract.datasets[name], today)
        # as já vistas como não publicadas por último: não ocupam o lugar do que existe e falta
        late = sorted(
            (p for p in gap["faltam"] if p != current), key=lambda p: (p in gap.get("aguardando", ()), -p)
        )
        # a janela do dataset diário é o `first_day` do YAML; nos demais, `limit` poupa a fonte
        keep = late if contract.datasets[name].partition == "day" else late[:limit]
        items += [(name, p) for p in keep]
    return items


def record_gaps(con: Connection, contract: SourceContract) -> None:
    """Grava em `fontes_verificacoes` (`particoes`) as partições de cada dataset: aviso se faltam, "
    "ok se não."""
    for name, gap in partition_gaps(con, contract).items():
        missing = gap["faltam"]
        detail = f"{gap['capturadas']} de {gap['esperadas']} partições"
        if gap["indisponiveis"]:
            detail += f"; a fonte não publica: {gap['indisponiveis']}"
        if missing:
            detail += f"; faltam: {missing}"
        monitoring.record(con, contract.source, name, None, "particoes", "warn" if missing else "ok", detail)


# ---------------------------------------------------------------- extração


def _not_yet_published(dataset: Dataset, year: int | None, error: fetch.SourceBlocked) -> bool:
    """Sem arquivo, não bloqueio: código de `missing_status` (ADR 0059) ou 403 no mês mais recente."""
    return error.status in dataset.missing_status or (
        error.status == 403
        and dataset.partition == "month"
        and year is not None
        and year >= current_partition(dataset, runs.today())
    )


def _latest_day(dataset: Dataset, value: int | None) -> bool:
    """O dia mais recente de um dataset diário: sem arquivo ainda não é falta."""
    return (
        dataset.partition == "day" and value is not None and value >= current_partition(dataset, runs.today())
    )


def _keep_previous(settings: Settings, previous: Mapping[str, Any], file: Path, lost: bool) -> None:
    """O download repetiu a captura anterior: o arquivo novo sai; se o antigo sumiu, o novo ocupa o lugar."""
    original = settings.storage_root / previous["caminho"]
    if file == original:
        return
    if lost:
        original.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(file, original)
    else:
        file.unlink()
    with suppress(OSError):  # a pasta só some se ficou vazia
        file.parent.rmdir()


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
    falhar, a falha é registrada em `metadata.fontes_verificacoes` e devolve -1, sem interromper o plano.
    """
    url = contract.url(dataset, year)
    downloader = downloader or fetch.downloader(contract, dataset)
    head_request = head_request or fetch.head_request(contract, dataset)
    with runs.track(con, "extract", contract.source, dataset, year) as run:
        previous = last_capture(con, url)
        try:
            headers = {} if force else head_request(url)
        except (OSError, fetch.SourceBlocked):  # HEAD brando: 403/405 não aborta; só o GET bloqueia
            headers = {}
        lost = previous is not None and not (settings.storage_root / previous["caminho"]).exists()
        if not force and previous is not None and not lost and unchanged(previous, headers):
            mark_checked(con, int(previous["id_captura"]))
            run.rows_in = 1
            return int(previous["id_captura"])
        reused = (
            None if force else same_file(con, contract, dataset, url, year, settings.storage_root, headers)
        )
        try:
            if reused:  # o pacote já veio por outro dataset: sem novo download
                file, digest, size = (
                    settings.storage_root / reused["caminho"],
                    reused["sha256"],
                    reused["qtd_bytes"],
                )
            else:
                file, digest, size = downloader(
                    url, folder(settings, contract.source, dataset, year, runs.now())
                )
        except fetch.SourceBlocked as error:
            if not _not_yet_published(contract.datasets[dataset], year, error):
                raise
            monitoring.record(
                con,
                contract.source,
                dataset,
                year,
                "availability",
                "error",
                f"mês em curso sem arquivo publicado ({error})",
                cd_status_http=error.status,
                tipo="nao_publicado",
            )
            return -1
        except (OSError, HTTPException) as error:
            code = error.code if isinstance(error, urllib.error.HTTPError) else None
            kind = "nao_encontrado" if code == 404 else "erro_http" if code else "falha_de_rede"
            if kind == "nao_encontrado" and _latest_day(contract.datasets[dataset], year):
                kind = "nao_publicado"  # o dia mais recente pode ainda não ter saído
            monitoring.record(
                con,
                contract.source,
                dataset,
                year,
                "availability",
                "error",
                str(error),
                cd_status_http=code,
                tipo=kind,
            )
            return -1
        if previous is not None and previous["sha256"] == digest:  # mesmo conteúdo: fica o arquivo antigo
            if not reused:  # o arquivo de outro dataset não se move nem se apaga
                _keep_previous(settings, previous, file, lost)
            mark_checked(con, int(previous["id_captura"]))
            run.rows_in = 1
            return int(previous["id_captura"])
        monitoring.record(
            con, contract.source, dataset, year, "availability", "ok", f"{size} bytes", bytes_recebidos=size
        )
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
    """Executa um plano, item a item. Devolve quantos itens foram processados (para no bloqueio).

    Com `recover` (a execução incremental), soma ao plano as partições passadas que faltam (`plan_recovery`).
    Se a fonte bloqueia (`SourceBlocked`), registra `bloqueio` e interrompe o resto dela.
    Ao fim, registra por dataset o estado das partições (`particoes` em `fontes_verificacoes`)."""
    if recover:
        items = [*items, *(i for i in plan_recovery(con, contract) if i not in items)]
    done = 0
    for dataset, year in items:
        logger.info("Extraindo %s", f"{dataset} {year or ''}".strip())
        try:
            extract(con, settings, contract, dataset, year, downloader, head_request, force)
            done += 1
            if (
                con.execute(  # um bloqueio antigo deixa de contar quando a fonte volta a responder
                    "SELECT count(*) FROM metadata.fontes_verificacoes WHERE fonte = ? AND dataset = ? AND "
                    "particao IS NOT DISTINCT FROM ? AND verificacao = 'bloqueio' AND resultado = 'error'",
                    (contract.source, dataset, year),
                ).fetchone()
                or (0,)
            )[0]:
                monitoring.record(con, contract.source, dataset, year, "bloqueio", "ok")
        except fetch.SourceBlocked as error:  # sem retry: o próximo agendamento tenta de novo
            monitoring.record(
                con,
                contract.source,
                dataset,
                year,
                "bloqueio",
                "error",
                str(error),
                cd_status_http=error.status,
                tipo="bloqueio",
            )
            logger.warning(
                "Fonte %s bloqueou (%s); o resto da fonte fica para a próxima execução",
                contract.source,
                error,
            )
            break
    record_gaps(con, contract)
    arquivos.materialize(con, settings, contract)  # coleções `arq_` do contrato (ADR 0037)
    privado.push_metadata(con, settings)
    return done
