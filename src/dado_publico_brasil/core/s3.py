"""Cliente S3 mínimo (PUT, DELETE e GET com SigV4, só biblioteca padrão) para o que o DuckDB não faz.

Serve a qualquer armazenamento compatível com S3 (hoje o R2): o `COPY` e o `glob` do DuckDB não gravam o
catálogo nem apagam objetos, e não listam bucket público. Não conhece nome de fonte nem de bucket.
"""

import base64
import hashlib
import hmac
import http.client
import threading
import time
import xml.etree.ElementTree as ET
from contextlib import nullcontext
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import quote

_LOCAL = threading.local()  # uma conexão HTTPS persistente por thread de envio
ATTEMPTS = 6  # tentativas por requisição


def sign(
    method: str,
    uri: str,
    params: str,
    headers: dict[str, str],
    payload: str,
    key_id: str,
    secret_key: str,
    stamp: str,
    region: str = "auto",
    service: str = "s3",
) -> str:
    """SigV4: devolve o valor do cabeçalho Authorization; `headers` já leva o `host`.

    `params` é a query já codificada e ordenada. Vetores da AWS em `tests/core/test_s3.py`.
    """
    nl = chr(10)
    day = stamp[:8]
    names = ";".join(sorted(headers))
    canonical = nl.join(
        [method, uri, params, *(f"{k}:{headers[k]}" for k in sorted(headers)), "", names, payload]
    )
    scope = f"{day}/{region}/{service}/aws4_request"
    to_sign = nl.join(["AWS4-HMAC-SHA256", stamp, scope, hashlib.sha256(canonical.encode()).hexdigest()])
    secret = ("AWS4" + secret_key).encode()
    for part in (day, region, service, "aws4_request"):
        secret = hmac.new(secret, part.encode(), hashlib.sha256).digest()
    signature = hmac.new(secret, to_sign.encode(), hashlib.sha256).hexdigest()
    return f"AWS4-HMAC-SHA256 Credential={key_id}/{scope}, SignedHeaders={names}, Signature={signature}"


def request(
    cfg: dict[str, str],
    method: str,
    key: str,
    path: Path | None = None,
    content_type: str | None = None,
    headers: dict[str, str] | None = None,
    query: dict[str, str] | None = None,
) -> bytes:
    """PUT (de um arquivo), DELETE ou GET assinado (SigV4) no R2: o que o COPY e o `glob` do DuckDB não fazem.

    `cfg` leva ACCOUNT_ID, ACCESS_KEY_ID, SECRET_ACCESS_KEY e BUCKET. `headers` somam-se aos assinados
    (Cache-Control...); num PUT segue o `x-amz-checksum-sha256` do arquivo. `query` são os parâmetros da URL
    (listagem). Devolve o corpo da resposta.
    """
    host = f"{cfg['ACCOUNT_ID']}.r2.cloudflarestorage.com"
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    uri = f"/{cfg['BUCKET']}/{quote(key)}"
    params = "&".join(f"{quote(k, safe='')}={quote(v, safe='')}" for k, v in sorted((query or {}).items()))
    signed_headers = {
        "host": host,
        "x-amz-content-sha256": "UNSIGNED-PAYLOAD",
        "x-amz-date": stamp,
        **{k.lower(): v for k, v in (headers or {}).items()},
    }
    if content_type:
        signed_headers["content-type"] = content_type
    if path:
        digest = hashlib.sha256()
        with path.open("rb") as f:
            while chunk := f.read(1 << 20):
                digest.update(chunk)
        signed_headers["x-amz-checksum-sha256"] = base64.b64encode(digest.digest()).decode()
    authorization = sign(
        method,
        uri,
        params,
        signed_headers,
        "UNSIGNED-PAYLOAD",
        cfg["ACCESS_KEY_ID"],
        cfg["SECRET_ACCESS_KEY"],
        stamp,
    )
    sent = {k: v for k, v in signed_headers.items() if k != "host"} | {"Authorization": authorization}
    if path:
        sent["Content-Length"] = str(path.stat().st_size)
    with path.open("rb") if path else nullcontext() as body:
        for attempt in range(
            1, ATTEMPTS + 1
        ):  # erro transitório (5xx, 429, conexão fechada): espera e tenta de novo
            conn = getattr(_LOCAL, "conn", None) or http.client.HTTPSConnection(host, timeout=3600)
            _LOCAL.conn = conn
            try:
                if body:
                    body.seek(0)
                conn.request(method, f"{uri}?{params}" if params else uri, body=body, headers=sent)
                response = conn.getresponse()
                detail = response.read()
                failure = None if response.status < 300 else f"HTTP {response.status} {detail[:200]!r}"
                retry = response.status == 429 or response.status >= 500
            except (http.client.HTTPException, OSError) as error:
                conn.close()
                _LOCAL.conn = None
                failure, retry = repr(error), True
            if failure is None:
                return detail
            if not retry or attempt == ATTEMPTS:
                raise RuntimeError(f"R2 {method} {key}: {failure}")
            time.sleep(min(2**attempt, 30))
    raise AssertionError("ATTEMPTS deve ser positivo")  # pragma: no cover


def list_objects(cfg: dict[str, str], prefix: str) -> dict[str, int]:
    """Chave e tamanho dos objetos sob `prefix` (ListObjectsV2 assinado, paginado por continuation-token)."""
    found: dict[str, int] = {}
    token = ""
    while True:
        query = {"list-type": "2", "prefix": prefix} | ({"continuation-token": token} if token else {})
        tree = ET.fromstring(request(cfg, "GET", "", query=query))
        for item in tree.iter():
            if item.tag.endswith("Contents"):
                fields = {c.tag.rsplit("}", 1)[-1]: (c.text or "") for c in item}
                found[fields["Key"]] = int(fields["Size"])
        fields = {c.tag.rsplit("}", 1)[-1]: (c.text or "") for c in tree}
        token = fields.get("NextContinuationToken", "")
        if fields.get("IsTruncated") != "true" or not token:
            return found
