"""Execução do dbt em outro processo.

O arquivo DuckDB aceita um processo escritor por vez e o dbt-duckdb mantém o arquivo aberto dentro
do processo; por isso o dbt roda em um subprocesso e o chamador precisa ter fechado a sua conexão.
O estado do dbt (logs e `target/`) fica dentro do storage, não na pasta do projeto.
"""

import json
import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from dado_publico_brasil.core.settings import DBT_DIR, Settings


@dataclass
class Outcome:
    returncode: int
    output: str
    results: list[dict[str, Any]] = field(default_factory=list)

    @property
    def failures(self) -> list[dict[str, Any]]:
        return [r for r in self.results if r["status"] in ("error", "fail", "runtime error")]


def target_dir(settings: Settings) -> Path:
    return settings.state_dir / "dbt" / "target"


def _command(settings: Settings, *args: str) -> tuple[list[str], dict[str, str]]:
    project = str(DBT_DIR)
    state = settings.state_dir / "dbt"
    command = [
        sys.executable,
        "-c",
        "from dbt.cli.main import cli; cli()",
        *args,
        "--project-dir",
        project,
        "--profiles-dir",
        project,
        "--log-path",
        str(state / "logs"),
        "--target-path",
        str(state / "target"),
    ]
    return command, {**os.environ, "DADO_PUBLICO_WAREHOUSE_FILE": str(settings.warehouse.resolve())}


def install_packages(settings: Settings) -> None:
    """Baixa os pacotes do dbt (`packages.yml`) na primeira vez; depois não precisa de rede."""
    if (DBT_DIR / "dbt_packages").exists():
        return
    project = str(DBT_DIR)
    command = [sys.executable, "-c", "from dbt.cli.main import cli; cli()", "deps"]
    command += ["--project-dir", project, "--profiles-dir", project]
    command += ["--log-path", str(settings.state_dir / "dbt" / "logs")]
    subprocess.run(command, check=True, capture_output=True)


def serve_docs(settings: Settings, port: int = 8080) -> int:
    """Gera e serve a documentação navegável do dbt (grafo de linhagem, tabelas e colunas).

    Bloqueia até o usuário interromper. A geração lê o warehouse: o pipeline precisa estar parado.
    """
    install_packages(settings)
    for args in (("docs", "generate"), ("docs", "serve", "--port", str(port))):
        command, env = _command(settings, *args)
        code = subprocess.call(command, env=env)
        if code != 0:
            return code
    return 0


def read_results(
    settings: Settings, results_file: str = "run_results.json", target: Path | None = None
) -> list[dict[str, Any]]:
    """Resultado de cada nó (modelo, teste, frescor) de uma execução do dbt (por padrão, a última)."""
    file = (target or target_dir(settings)) / results_file
    if not file.exists():
        return []
    return [
        {
            "unique_id": item.get("unique_id", ""),
            "status": str(item.get("status", "")),
            "failures": item.get("failures"),
            "message": item.get("message"),
        }
        for item in json.loads(file.read_text(encoding="utf-8")).get("results", [])
    ]


def invoke(settings: Settings, *args: str, results_file: str = "run_results.json") -> Outcome:
    """Roda `dbt <args>` no projeto da camada de dados e lê o arquivo de resultados."""
    install_packages(settings)
    command, env = _command(settings, *args)
    process = subprocess.run(command, env=env, capture_output=True, text=True, check=False)
    results = read_results(settings, results_file)
    return Outcome(process.returncode, (process.stdout + process.stderr)[-2000:], results)
