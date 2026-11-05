"""O `.env` é lido por padrão pelo CLI, sem sobrescrever o que o ambiente já define."""

from pathlib import Path

import pytest

from dado_publico_brasil.core.settings import load_env_file


def test_env_file_fills_missing_variables_and_never_overrides(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env = tmp_path / ".env"
    env.write_text(
        "# comentário\n\nDPB_TESTE_A=um\nDPB_TESTE_B = 'dois com espaço'\nDPB_TESTE_C=\"três\"\nDPB_TESTE_D=do_arquivo\nsem_igual\n",
        encoding="utf-8",
    )
    for k in ("DPB_TESTE_A", "DPB_TESTE_B", "DPB_TESTE_C"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("DPB_TESTE_D", "do_ambiente")

    load_env_file(env)

    import os

    assert os.environ["DPB_TESTE_A"] == "um"
    assert os.environ["DPB_TESTE_B"] == "dois com espaço"
    assert os.environ["DPB_TESTE_C"] == "três"
    assert os.environ["DPB_TESTE_D"] == "do_ambiente"  # o ambiente vence o arquivo


def test_missing_env_file_is_ignored(tmp_path: Path) -> None:
    load_env_file(tmp_path / "nao_existe.env")
