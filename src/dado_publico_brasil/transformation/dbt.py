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
from dado_publico_brasil.transformation import branding


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


def prune_static(html: str, project: str = "dado_publico_brasil") -> str:
    """Tira do site estático do dbt o que não é do projeto: pacotes (Elementary, dbt_utils...) e exposures.

    O dbt embute `{manifest:{...},catalog:{...}}` no HTML e não tem opção para ocultar pacotes inteiros.
    """
    start = html.index("{manifest:") + len("{manifest:")
    manifest, end = json.JSONDecoder().raw_decode(html, start)
    catalog_start = html.index(",catalog:", end) + len(",catalog:")
    catalog, catalog_end = json.JSONDecoder().raw_decode(html, catalog_start)
    drop = {k for k, n in manifest["nodes"].items() if n.get("package_name") != project}
    manifest["nodes"] = {k: v for k, v in manifest["nodes"].items() if k not in drop}
    manifest["macros"] = {k: v for k, v in manifest["macros"].items() if v.get("package_name") == project}
    drop |= set(manifest["exposures"])
    manifest["exposures"] = {}
    for graph in ("parent_map", "child_map"):
        manifest[graph] = {
            k: [x for x in v if x not in drop] for k, v in manifest[graph].items() if k not in drop
        }
    catalog["nodes"] = {k: v for k, v in catalog["nodes"].items() if k not in drop}
    return (
        html[:start]
        + json.dumps(manifest)
        + html[end:catalog_start]
        + json.dumps(catalog)
        + html[catalog_end:]
    )


def static_docs(settings: Settings) -> Path:
    """Gera o site do dbt em um único HTML (`docs generate --static`), só com o projeto."""
    outcome = invoke(settings, "docs", "generate", "--static")
    if outcome.returncode != 0:
        raise RuntimeError(f"dbt docs generate falhou: {outcome.output}")
    file = target_dir(settings) / "static_index.html"
    html = prune_static(file.read_text(encoding="utf-8"))
    file.write_text(branding.apply(html, "Dado Público Brasil · Tabelas"), encoding="utf-8")
    return file


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


def invoke(
    settings: Settings, *args: str, results_file: str = "run_results.json", stream: bool = False
) -> Outcome:
    """Roda `dbt <args>` no projeto da camada de dados e lê o arquivo de resultados.

    Com `stream`, a saída do dbt (uma linha por modelo e teste) sai na hora, para acompanhar o progresso."""
    install_packages(settings)
    command, env = _command(settings, *args)
    with subprocess.Popen(
        command, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, errors="replace"
    ) as process:
        output = ""
        for line in process.stdout or ():
            if stream:
                print(line, end="", flush=True)
            output = (output + line)[-2000:]
    results = read_results(settings, results_file)
    return Outcome(process.returncode, output, results)
