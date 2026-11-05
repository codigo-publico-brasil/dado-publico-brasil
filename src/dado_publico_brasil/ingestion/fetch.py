"""Buscar: obter os bytes da origem. É o único ponto que sabe falar com a fonte.

O padrão serve a qualquer URL que devolva um arquivo ou um JSON (CSV em lote, API REST): GET com nova
tentativa em falha de rede ou 5xx, cabeçalhos da declaração da fonte e pergunta barata (HEAD) para saber
se mudou. Credenciais entram como `${VARIAVEL}` nos cabeçalhos do YAML e vêm do ambiente (`.env`), nunca
do repositório. Uma fonte que precise de outro jeito (SOAP, robô, pacote compactado...) tem um módulo em
`ingestion/custom/<poder>/<esfera>/<fonte>.py` com `download(url, folder)` e/ou `head(url)`; o resto do
pipeline não muda, porque a saída é sempre um arquivo com hash.
"""

import gzip
import hashlib
import os
import re
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from contextlib import suppress
from functools import partial
from http.client import HTTPException
from pathlib import Path
from string import Template
from typing import IO, Any
from urllib.parse import urlparse

from dado_publico_brasil.ingestion.contract import SourceContract

Downloader = Callable[[str, Path], tuple[Path, str, int]]
HeadRequest = Callable[[str], dict[str, str | None]]

AGENT = "dado-publico-brasil/0.1 (projeto civico aberto; +https://github.com/codigo-publico-brasil/dado-publico-brasil)"
CHUNK = 1024 * 1024
TRIES = 3


class SourceBlocked(Exception):
    """A fonte nos barrou (403/429, HTML no lugar do arquivo, outro host): não se insiste."""


class Pace:
    """Cortesia: intervalo mínimo entre requisições (`access.rate_limit`); relógio e espera injetáveis."""

    def __init__(
        self,
        rate: float,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.interval, self.clock, self.sleep = 1 / rate, clock, sleep
        self.last: float | None = None

    def wait(self) -> None:
        if self.last is not None and (pause := self.last + self.interval - self.clock()) > 0:
            self.sleep(pause)
        self.last = self.clock()


_PACES: dict[tuple[str, float], Pace] = {}  # por fonte e taxa; não é thread-safe (um extrator por vez)
SECOND_LEVEL = {"gov", "leg", "jus", "mp", "com", "org", "net", "edu", "mil"}  # ex.: camara.leg.br


def _site(url: str) -> str:
    """O domínio registrável do endereço (`www.in.gov.br` e `in.gov.br` são o mesmo site)."""
    labels = (urlparse(url).hostname or "").split(".")
    return ".".join(labels[-3:] if len(labels) > 2 and labels[-2] in SECOND_LEVEL else labels[-2:])


def pace_of(contract: SourceContract) -> Pace:
    return _PACES.setdefault((contract.source, contract.rate_limit), Pace(contract.rate_limit))


def _open(
    url: str,
    headers: dict[str, str],
    method: str,
    timeout: int,
    pace: Pace | None,
    suffix: str = "csv",
    sites: tuple[str, ...] = (),
) -> Any:
    """Abre a requisição respeitando a cortesia; levanta `SourceBlocked` antes de qualquer gravação.

    Redirecionar para outro site é bloqueio, salvo para os de `access.redirect_sites` da fonte."""
    if pace:
        pace.wait()
    try:
        response = urllib.request.urlopen(_request(url, headers, method), timeout=timeout)
    except urllib.error.HTTPError as error:
        if error.code in (403, 429):
            raise SourceBlocked(f"{url}: HTTP {error.code}") from error
        raise
    if _site(response.url) not in (_site(url), *sites):
        response.close()
        raise SourceBlocked(f"{url}: redirecionou para {response.url}")
    if suffix != "html" and "text/html" in (response.headers.get("Content-Type") or "").lower():
        response.close()
        raise SourceBlocked(f"{url}: HTML no lugar do arquivo")
    return response


def _request(url: str, headers: dict[str, str], method: str = "GET") -> urllib.request.Request:
    expanded = {k: Template(v).substitute(os.environ) for k, v in headers.items()}
    return urllib.request.Request(url, method=method, headers={"User-Agent": AGENT, **expanded})


def _body(response: Any) -> IO[bytes]:
    """O corpo da resposta como o documento é.

    Se a fonte comprime no transporte (`Content-Encoding: gzip`, como a API do IBGE faz mesmo quando se pede
    `identity`), descomprime: a compressão de transporte não faz parte do documento."""
    if (response.headers.get("Content-Encoding") or "").lower() == "gzip":
        return gzip.GzipFile(fileobj=response)  # type: ignore[return-value]
    return response  # type: ignore[no-any-return]


def _retrying[T](call: Callable[[], T]) -> T:
    """Repete em falha de rede ou erro 5xx; erro 4xx é definitivo."""
    for attempt in range(TRIES):
        try:
            return call()
        except urllib.error.HTTPError as error:
            if error.code < 500 or attempt == TRIES - 1:
                raise
        except (OSError, HTTPException):
            if attempt == TRIES - 1:
                raise
        time.sleep(2**attempt)
    raise AssertionError("inalcançável")


def download(
    url: str,
    folder: Path,
    headers: dict[str, str] | None = None,
    suffix: str = "csv",
    name: str | None = None,
    pace: Pace | None = None,
    sites: tuple[str, ...] = (),
) -> tuple[Path, str, int]:
    """Baixa sem alterar. Devolve o caminho (com o hash no nome), o SHA-256 e o tamanho em bytes.

    O nome do arquivo vem do fim da URL, ou de `name` quando a URL não termina no nome do arquivo."""
    temporary = folder / "download.tmp"

    def attempt() -> tuple[str, int]:
        sha, size = hashlib.sha256(), 0
        with _open(url, headers or {}, "GET", 120, pace, suffix, sites) as r:
            folder.mkdir(parents=True, exist_ok=True)  # só depois de aberta: bloqueio não deixa pasta vazia
            with temporary.open("wb") as f:
                body = _body(r)
                while chunk := body.read(CHUNK):
                    f.write(chunk)
                    sha.update(chunk)
                    size += len(chunk)
            promised = r.headers.get("Content-Length")
            # a leitura em pedaços não acusa conexão cortada; sem transporte comprimido o tamanho tem de bater
            if (
                promised
                and promised.isdigit()
                and not r.headers.get("Content-Encoding")
                and int(promised) != size
            ):
                raise OSError(f"download truncado: recebidos {size} bytes, a fonte informou {promised}")
        return sha.hexdigest(), size

    try:
        digest, size = _retrying(attempt)
    except BaseException:  # nada incompleto fica no landing: o temporário some e a pasta, se vazia
        temporary.unlink(missing_ok=True)
        with suppress(OSError):
            folder.rmdir()
        raise
    name = re.sub(r"[^\w.-]+", "_", name or url.rsplit("/", 1)[-1])
    stem, dot, extension = name.rpartition(".")
    stem, extension = (
        (stem, extension) if dot and extension in ("csv", "json", "zip", "xml") else (name, suffix)
    )
    target = folder / f"{stem}-{digest[:12]}.{extension}"
    if target.exists():
        temporary.unlink()
    else:
        temporary.rename(target)
    return target, digest, size


def get(url: str, headers: dict[str, str] | None = None) -> tuple[int, bytes]:
    """GET de um item. Devolve (status, corpo); erro 4xx, 5xx (depois das tentativas) e falta de resposta
    (status 0) viram resultado, não exceção: quem chama registra e segue."""

    def attempt() -> tuple[int, bytes]:
        try:
            with urllib.request.urlopen(_request(url, headers or {}), timeout=120) as response:
                return int(response.status), _body(response).read()
        except urllib.error.HTTPError as error:
            if error.code >= 500:
                raise
            return error.code, error.read()

    try:
        return _retrying(attempt)
    except urllib.error.HTTPError as error:
        return error.code, b""
    except (OSError, HTTPException):
        return 0, b""


def head(
    url: str,
    headers: dict[str, str] | None = None,
    pace: Pace | None = None,
    suffix: str = "csv",
    sites: tuple[str, ...] = (),
) -> dict[str, str | None]:
    """Pergunta à fonte (HEAD) se o arquivo mudou, sem baixá-lo. Valores ausentes ficam `None`."""
    with _open(url, headers or {}, "HEAD", 60, pace, suffix, sites) as response:
        return {
            "etag": response.headers.get("ETag"),
            "last_modified": response.headers.get("Last-Modified"),
            "size": response.headers.get("Content-Length"),
        }


def downloader(contract: SourceContract, dataset: str) -> Downloader:
    """O `download` do módulo `custom` da fonte, se houver, ou o padrão com os cabeçalhos do YAML."""
    custom = getattr(contract.custom, "download", None)
    suffix = "zip" if contract.datasets[dataset].archive == "zip" else contract.format_of(dataset)
    return custom or partial(
        download,
        headers=contract.headers_of(dataset),
        suffix=suffix,
        pace=pace_of(contract),
        sites=contract.redirect_sites,
    )


def head_request(contract: SourceContract, dataset: str) -> HeadRequest:
    custom = getattr(contract.custom, "head", None)
    suffix = contract.format_of(dataset)
    return custom or partial(
        head,
        headers=contract.headers_of(dataset),
        pace=pace_of(contract),
        suffix=suffix,
        sites=contract.redirect_sites,
    )
