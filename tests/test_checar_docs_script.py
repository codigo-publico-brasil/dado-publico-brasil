"""scripts/checar-docs.sh: o PR que muda código sem documentação só passa com a declaração `Docs: não se aplica`."""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.skipif(shutil.which("bash") is None, reason="precisa do bash")


def roda(arquivos: str, body: str = "") -> int:
    r = subprocess.run(
        ["bash", "scripts/checar-docs.sh"], cwd=ROOT, input=arquivos, text=True, capture_output=True,
        env={**os.environ, "PR_BODY": body}, encoding="utf-8", timeout=30,
    )  # fmt: skip
    return r.returncode


@pytest.mark.parametrize(
    ("arquivos", "body", "codigo"),
    [
        ("src/a.py\ntests/t.py\n", "", 1),  # código sem docs e sem declaração
        ("sources/x.yml\n", "Docs: nao se aplica", 1),  # declaração fora do formato
        ("src/a.py\ndocs/02-fazer/x.md\n", "", 0),  # com docs
        ("dbt/m.sql\nREADME.md\n", "", 0),
        ("ddl/1.sql\nAGENTS.md\n", "", 0),
        ("src/a.py\n", "Resumo\n\nDocs: não se aplica — só refatoração interna\n", 0),  # com declaração
        ("tests/t.py\n.github/workflows/ci.yml\n", "", 0),  # só tests e esteira
    ],
)
def test_checar_docs(arquivos: str, body: str, codigo: int) -> None:
    assert roda(arquivos, body) == codigo
