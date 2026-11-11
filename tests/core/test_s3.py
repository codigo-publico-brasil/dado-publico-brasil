"""Assinatura SigV4 do cliente S3 mínimo, contra os vetores públicos da AWS, e o PUT assinado do R2."""

import base64
import hashlib
import http.client
import threading
from pathlib import Path

import pytest

from dado_publico_brasil.core import s3

# Vetores da suíte pública de testes de SigV4 da AWS (`aws-sig-v4-test-suite`), na cópia do botocore, com a
# chave e o segredo de exemplo da documentação:
# https://github.com/boto/botocore/tree/develop/tests/unit/auth/aws4_testsuite
KEY, SECRET, STAMP = "AKIDEXAMPLE", "wJalrXUtnFEMI/K7MDENG+bPxRfiCYEXAMPLEKEY", "20150830T123600Z"
EMPTY = hashlib.sha256(b"").hexdigest()


def test_signature_matches_the_aws_get_vanilla_vector() -> None:
    headers = {"host": "example.amazonaws.com", "x-amz-date": STAMP}
    auth = s3.sign("GET", "/", "", headers, EMPTY, KEY, SECRET, STAMP, "us-east-1", "service")
    assert auth == (
        "AWS4-HMAC-SHA256 Credential=AKIDEXAMPLE/20150830/us-east-1/service/aws4_request, "
        "SignedHeaders=host;x-amz-date, "
        "Signature=5fa00fa31553b73ebf1942676e86291e8372ff2a2260956d9b8aae1d763fbf31"
    )


def test_signature_matches_the_aws_query_vector() -> None:
    headers = {"host": "example.amazonaws.com", "x-amz-date": STAMP}
    auth = s3.sign(  # get-vanilla-query-order-key-case: a query chega ordenada
        "GET", "/", "Param1=value1&Param2=value2", headers, EMPTY, KEY, SECRET, STAMP, "us-east-1", "service"
    )
    assert auth.endswith("Signature=b97d918cfa904a5beff61c982a1b6f458b799221646efd99d3219ec94cdf2500")


def test_the_signed_upload_carries_content_type_cache_control_and_checksum(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    seen: dict[str, str] = {}

    class Response:
        status = 200

        def read(self) -> bytes:
            return b""

    class Conn:
        def __init__(self, host: str, timeout: int) -> None: ...

        def request(self, method: str, uri: str, body: object, headers: dict[str, str]) -> None:
            seen.update({k.lower(): v for k, v in headers.items()})

        def getresponse(self) -> Response:
            return Response()

        def close(self) -> None: ...

    cfg = dict.fromkeys(("ACCOUNT_ID", "ACCESS_KEY_ID", "SECRET_ACCESS_KEY", "BUCKET"), "x")
    monkeypatch.setattr(http.client, "HTTPSConnection", Conn)
    monkeypatch.setattr(s3, "_LOCAL", threading.local())
    file = tmp_path / "f.jpg"
    file.write_bytes(b"abc")
    s3.request(cfg, "PUT", "k/f.jpg", file, "image/jpeg", {"Cache-Control": "public"})
    assert seen["content-type"] == "image/jpeg" and seen["cache-control"] == "public"
    assert seen["x-amz-checksum-sha256"] == base64.b64encode(hashlib.sha256(b"abc").digest()).decode()
    assert "cache-control" in seen["authorization"] and "x-amz-checksum-sha256" in seen["authorization"]
