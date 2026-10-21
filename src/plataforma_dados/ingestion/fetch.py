"""Buscar: obter os bytes da origem. É o único ponto que sabe falar com a fonte.

O padrão serve a qualquer URL que devolva um arquivo ou um JSON (CSV em lote, API REST): GET com nova
tentativa em falha de rede ou 5xx, cabeçalhos da declaração da fonte e pergunta barata (HEAD) para saber
se mudou. Credenciais entram como `${VARIAVEL}` nos cabeçalhos do YAML e vêm do ambiente (`.env`), nunca do
repositório. Uma fonte que precise de outro jeito (SOAP, robô, pacote compactado...) traz um `custom.py` na
sua pasta e define `download(url, folder)` e/ou `head(url)`; o resto do pipeline não muda, porque a saída
é sempre um arquivo com hash.
"""

import hashlib
import os
import re
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from functools import partial
from http.client import HTTPException
from pathlib import Path
from string import Template

from plataforma_dados.ingestion.contract import SourceContract

Downloader = Callable[[str, Path], tuple[Path, str, int]]
HeadRequest = Callable[[str], dict[str, str | None]]

AGENT = "plataforma-dados/0.1 (projeto civico aberto)"
CHUNK = 1024 * 1024
TRIES = 3


def _request(url: str, headers: dict[str, str], method: str = "GET") -> urllib.request.Request:
    expanded = {k: Template(v).substitute(os.environ) for k, v in headers.items()}
    return urllib.request.Request(url, method=method, headers={"User-Agent": AGENT, **expanded})


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
    url: str, folder: Path, headers: dict[str, str] | None = None, suffix: str = "csv"
) -> tuple[Path, str, int]:
    """Baixa sem alterar. Devolve o caminho (com o hash no nome), o SHA-256 e o tamanho em bytes."""
    folder.mkdir(parents=True, exist_ok=True)
    temporary = folder / "download.tmp"

    def attempt() -> tuple[str, int]:
        sha, size = hashlib.sha256(), 0
        with (
            urllib.request.urlopen(_request(url, headers or {}), timeout=120) as r,
            temporary.open("wb") as f,
        ):
            while chunk := r.read(CHUNK):
                f.write(chunk)
                sha.update(chunk)
                size += len(chunk)
        return sha.hexdigest(), size

    digest, size = _retrying(attempt)
    name = re.sub(r"[^\w.-]+", "_", url.rsplit("/", 1)[-1])
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


def head(url: str, headers: dict[str, str] | None = None) -> dict[str, str | None]:
    """Pergunta à fonte (HEAD) se o arquivo mudou, sem baixá-lo. Valores ausentes ficam `None`."""
    with urllib.request.urlopen(_request(url, headers or {}, "HEAD"), timeout=60) as response:
        return {
            "etag": response.headers.get("ETag"),
            "last_modified": response.headers.get("Last-Modified"),
            "size": response.headers.get("Content-Length"),
        }


def downloader(contract: SourceContract) -> Downloader:
    """O `download` da fonte: o do `custom.py`, se houver, ou o padrão com os cabeçalhos do YAML."""
    custom = getattr(contract.custom, "download", None)
    return custom or partial(download, headers=contract.headers, suffix=contract.format)


def head_request(contract: SourceContract) -> HeadRequest:
    custom = getattr(contract.custom, "head", None)
    return custom or partial(head, headers=contract.headers)
