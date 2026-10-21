"""Dataset por item (`load: foreach`): uma chamada para cada linha de outro dataset da mesma fonte.

Os itens saem do raw do dataset de origem (`foreach.from`, com `where` opcional). Cada execução busca os
itens que faltam ou mudaram, em lotes: cada lote vira um arquivo do landing (ver `batch.py`) com a resposta
byte a byte de cada item, e `metadata.capture_items` registra status, hash e versão de cada um. Um lote
pronto já está registrado, então uma execução interrompida continua de onde parou. A taxa é a da fonte
(`access.rate_limit`). Item novo, item cuja `version` mudou, item com falha e item antigo
(`refresh_after_days`) são buscados de novo; resposta 404 não é repetida.
"""

import hashlib
import time
from collections.abc import Callable
from datetime import UTC, datetime
from functools import partial
from itertools import batched
from typing import Any

from plataforma_dados.core import runs
from plataforma_dados.core.settings import Settings
from plataforma_dados.core.warehouse import Connection, rows
from plataforma_dados.ingestion import batch, fetch, landing, monitoring
from plataforma_dados.ingestion.contract import SourceContract
from plataforma_dados.ingestion.loader import normalize

Get = Callable[[str], tuple[int, bytes]]
MAX = 10**12  # "todos"


def _items(con: Connection, contract: SourceContract, name: str) -> list[tuple[str, str | None]]:
    """Itens do dataset, os mais recentes primeiro, com a versão atual de cada um."""
    f = contract.datasets[name].foreach
    assert f
    version = f"max(CAST({f.version} AS VARCHAR))" if f.version else "NULL"
    recent = f"max({f.recent_by})" if f.recent_by else "NULL"
    found = con.execute(
        f"SELECT CAST({f.item} AS VARCHAR) AS item, {version} AS version "
        f"FROM {contract.schema}.{normalize(f.source)} WHERE ({f.where}) AND {f.item} IS NOT NULL "
        f"GROUP BY 1 ORDER BY {recent} DESC NULLS LAST, 1 DESC"
    ).fetchall()
    return [(str(i), v) for i, v in found]


def _latest(con: Connection, contract: SourceContract, name: str) -> dict[str, dict[str, Any]]:
    """A busca mais recente de cada item."""
    found = rows(
        con,
        "SELECT item, status, version, fetched_at FROM metadata.capture_items "
        "WHERE source = ? AND dataset = ? QUALIFY ROW_NUMBER() OVER (PARTITION BY item ORDER BY id DESC) = 1",
        (contract.source, name),
    )
    return {r["item"]: r for r in found}


def _is_pending(
    contract: SourceContract, name: str, version: str | None, last: dict[str, Any] | None
) -> bool:
    f = contract.datasets[name].foreach
    assert f
    if last is None:
        return True
    changed = f.version is not None and last["version"] != version
    if last["status"] == 404:
        return changed  # a fonte não tem o item; só tenta de novo se ele mudou
    if last["status"] != 200:
        return True  # falha: tenta de novo
    if changed:
        return True
    if f.refresh_after_days is not None:
        age = datetime.now(UTC) - datetime.fromisoformat(last["fetched_at"])
        return age.days >= f.refresh_after_days
    return False


def pending(con: Connection, contract: SourceContract, name: str) -> list[tuple[str, str | None]]:
    latest = _latest(con, contract, name)
    return [(i, v) for i, v in _items(con, contract, name) if _is_pending(contract, name, v, latest.get(i))]


def coverage(con: Connection, contract: SourceContract, name: str) -> dict[str, int]:
    """Quantos itens esperados já foram buscados, não existem na fonte (404), falharam ou ainda faltam."""
    items = _items(con, contract, name)
    latest = _latest(con, contract, name)
    status = [latest[i]["status"] if i in latest else None for i, _ in items]
    return {
        "esperados": len(items),
        "obtidos": status.count(200),
        "inexistentes": status.count(404),
        "falhas": sum(1 for s in status if s not in (None, 200, 404)),
        "faltam": len(pending(con, contract, name)),
    }


def capture(
    con: Connection,
    settings: Settings,
    contract: SourceContract,
    name: str,
    limit: int = MAX,
    get: Get | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> int:
    """Busca até `limit` itens pendentes (os mais recentes primeiro). Devolve quantos foram buscados."""
    dataset = contract.datasets[name]
    f = dataset.foreach
    assert f
    get = get or partial(fetch.get, headers=contract.headers_of(name))
    todo = pending(con, contract, name)[:limit]
    interval = 1 / contract.rate_limit
    last_call = 0.0
    done = 0
    with runs.track(con, "extract", contract.source, name) as run:
        for n, chunk in enumerate(batched(todo, f.batch_size, strict=False)):
            envelopes = []
            for item, version in chunk:
                wait = last_call + interval - time.monotonic()
                if wait > 0:
                    sleep(wait)
                last_call = time.monotonic()
                url = contract.item_url(name, item)
                status, body = get(url)
                envelopes.append((batch.envelope(item, url, status, body, runs.now()), version))
            _register(con, settings, contract, name, run.id, n, envelopes)
            done += len(chunk)
            print(f"{name}: {done}/{len(todo)} itens", flush=True)
        run.rows_in = run.rows_out = done
    if done:
        counts = coverage(con, contract, name)
        detail = ", ".join(f"{k} {v}" for k, v in counts.items())
        status_ok = "ok" if counts["falhas"] == 0 else "warn"
        monitoring.record(con, contract.source, name, None, "coverage", status_ok, detail)
    return done


def _register(
    con: Connection,
    settings: Settings,
    contract: SourceContract,
    name: str,
    run_id: int,
    number: int,
    envelopes: list[tuple[batch.Envelope, str | None]],
) -> None:
    folder = settings.landing_dir / contract.source
    folder.mkdir(parents=True, exist_ok=True)
    file = folder / f"{name}-lote-{run_id}-{number}.jsonl.gz"
    batch.write(file, (e for e, _ in envelopes))
    digest = hashlib.sha256(file.read_bytes()).hexdigest()
    relative = file.relative_to(settings.storage_root).as_posix()
    capture_id = landing.register_capture(
        con,
        contract.source,
        name,
        None,
        f"foreach:{contract.source}/{name}/{run_id}-{number}",
        digest,
        file.stat().st_size,
        relative,
        run_id,
    )
    con.executemany(
        "INSERT INTO metadata.capture_items (capture_id, source, dataset, item, url, status, sha256, "
        "fetched_at, version) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            (
                capture_id,
                contract.source,
                name,
                e["item"],
                e["url"],
                e["status"],
                e["sha256"],
                e["buscado_em"],
                v,
            )
            for e, v in envelopes
        ],
    )
    monitoring.check_header(con, contract, contract.datasets[name], None, file)


def verify(con: Connection, settings: Settings, source: str | None = None) -> list[str]:
    """Confere o landing: o hash de cada arquivo, o de cada resposta dentro dos lotes e o índice
    `capture_items`. Devolve os problemas encontrados (lista vazia = tudo íntegro)."""
    problems: list[str] = []
    where, args = ("WHERE source = ?", (source,)) if source else ("", ())
    for c in rows(con, f"SELECT id, path, sha256, url FROM metadata.captures {where} ORDER BY id", args):
        file = settings.storage_root / c["path"]
        if not file.exists():
            problems.append(f"captura {c['id']}: arquivo ausente ({c['path']})")
        elif hashlib.sha256(file.read_bytes()).hexdigest() != c["sha256"]:
            problems.append(f"captura {c['id']}: o arquivo mudou depois da captura ({c['path']})")
        elif c["url"].startswith("foreach:"):
            indexed = {
                (r["item"], r["sha256"])
                for r in rows(
                    con, "SELECT item, sha256 FROM metadata.capture_items WHERE capture_id = ?", (c["id"],)
                )
            }
            seen = set()
            for e in batch.read(file):
                if hashlib.sha256(batch.body(e)).hexdigest() != e["sha256"]:
                    problems.append(f"captura {c['id']}, item {e['item']}: a resposta não bate com o hash")
                seen.add((e["item"], e["sha256"]))
            if seen != indexed:
                problems.append(f"captura {c['id']}: o lote e metadata.capture_items divergem")
    return problems
