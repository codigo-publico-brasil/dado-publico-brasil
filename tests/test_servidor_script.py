"""scripts/servidor.sh: o `--dry-run` imprime os comandos esperados e o modelo do .env não traz segredo."""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
EXEMPLO = ROOT / ".env.servidor.example"
DC = "docker --context servidor compose --env-file"

pytestmark = pytest.mark.skipif(shutil.which("bash") is None, reason="precisa do bash")


def dry(*args: str, tmp: Path) -> str:
    (tmp / "dados" / "landing").mkdir(parents=True, exist_ok=True)
    (tmp / "dados" / "landing" / "a.txt").write_text("x")
    env = {**os.environ, "SERVIDOR_ENV_FILE": str(EXEMPLO), "DADO_PUBLICO_STORAGE_ROOT": str(tmp / "dados")}
    r = subprocess.run(
        ["bash", "scripts/servidor.sh", *args, "--dry-run"],
        cwd=ROOT, env=env, capture_output=True, text=True, encoding="utf-8", timeout=60, stdin=subprocess.DEVNULL,
    )  # fmt: skip
    assert r.returncode == 0, r.stderr
    return r.stdout


def test_exemplo_nao_tem_segredo() -> None:
    for linha in EXEMPLO.read_text(encoding="utf-8").splitlines():
        chave, _, valor = linha.partition("=")
        if any(s in chave for s in ("KEY", "SECRET", "PASSWORD", "DSN", "TOKEN", "R2_", "LAKE_URL")):
            assert not valor.strip(), f"{chave} deve ficar vazio no modelo"
    assert "COMPOSE_FILE=compose.yaml,compose.servidor.yaml" in EXEMPLO.read_text(encoding="utf-8")


def test_implantar_nunca_lanca_o_atualizar_tudo(tmp_path: Path) -> None:
    out = dry("implantar", tmp=tmp_path)
    for esperado in ("pull webserver daemon", "up -d webserver daemon", "ps -a"):
        assert esperado in out
    assert "atualizar_tudo" not in out and "implantado" not in out
    assert DC in out


def test_primeira_carga_tem_trava_e_ordem(tmp_path: Path) -> None:
    out = dry("primeira-carga", tmp=tmp_path)
    assert "ativas" in out  # trava de execução em andamento
    for esperado in (
        "up -d webserver",
        "dagster job launch -m dado_publico_brasil.orchestration.definitions -j atualizar_tudo",
        "up -d daemon",
    ):
        assert esperado in out
    assert out.index("up -d webserver") < out.index("-j atualizar_tudo") < out.index("up -d daemon")


def test_status_e_dados(tmp_path: Path) -> None:
    out = dry("status", tmp=tmp_path)
    assert "stats --no-stream" in out
    assert "http://127.0.0.1:3000/server_info" in out  # DADO_PUBLICO_BIND:DADO_PUBLICO_PORT do .env.servidor
    assert "landing" in dry("dados", tmp=tmp_path)


def test_preparar_cria_contexto_com_a_porta(tmp_path: Path) -> None:
    out = dry("preparar", "usuario@exemplo", "2222", tmp=tmp_path)
    assert "host=ssh://usuario@exemplo:2222" in out
    assert "authorized_keys" in out
