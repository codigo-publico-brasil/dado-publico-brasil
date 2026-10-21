"""Lote de respostas: o arquivo do landing de um dataset por item (`foreach`).

Um lote é um `.jsonl.gz` com um envelope por linha: `{item, url, status, buscado_em, sha256, corpo}`. O
`corpo` é a resposta da fonte exatamente como veio (texto; em base64 se não for UTF-8) e o `sha256` é o do
corpo, para auditar cada resposta sem baixar de novo. O gzip é determinístico (mesmo conteúdo, mesmo hash).
"""

import base64
import gzip
import hashlib
import io
import json
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Any

Envelope = dict[str, Any]


def envelope(item: str, url: str, status: int, body: bytes, fetched_at: str) -> Envelope:
    found: Envelope = {
        "item": item,
        "url": url,
        "status": status,
        "buscado_em": fetched_at,
        "sha256": hashlib.sha256(body).hexdigest(),
    }
    try:
        found["corpo"] = body.decode("utf-8")
    except UnicodeDecodeError:
        found["corpo_b64"] = base64.b64encode(body).decode("ascii")
    return found


def body(found: Envelope) -> bytes:
    """O corpo da resposta, byte a byte."""
    if "corpo_b64" in found:
        return base64.b64decode(found["corpo_b64"])
    return str(found["corpo"]).encode("utf-8")


def write(path: Path, envelopes: Iterable[Envelope]) -> None:
    buffer = io.BytesIO()
    with gzip.GzipFile(fileobj=buffer, mode="wb", mtime=0) as f:
        for found in envelopes:
            f.write(json.dumps(found, ensure_ascii=True).encode("ascii") + b"\n")
    path.write_bytes(buffer.getvalue())


def read(path: Path) -> Iterator[Envelope]:
    with gzip.open(path, "rt", encoding="ascii") as f:
        for line in f:
            yield json.loads(line)
