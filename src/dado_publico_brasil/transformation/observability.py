"""Relatório de saúde dos dados (ADR 0018) e alerta por e-mail.

Reúne o que as camadas de verificação já gravaram em `metadata`: o monitor das fontes e o balanço de cada
carga (`source_checks`), os testes do dbt e as anomalias que o Elementary detecta nos marts (volume,
colunas que mudam, nulos). Nada aqui interrompe o pipeline: `dado-publico observe` resume e falha (código de
saída 1) se houver problema, e `notify` manda o resumo por e-mail quando há.
"""

import os
import shutil
import smtplib
import subprocess
from pathlib import Path

from dado_publico_brasil.core import alert
from dado_publico_brasil.core.settings import DBT_DIR, Settings
from dado_publico_brasil.core.warehouse import Connection

ELEMENTARY = "0.26.1"  # a mesma versão do pacote dbt em dbt/packages.yml

ANOMALIES = (
    "SELECT status, unique_id, failures, message FROM metadata.dbt_results WHERE run_id = "
    "(SELECT max(id) FROM metadata.runs WHERE stage = 'transform_post' AND source = 'dbt') "
    "AND status IN ('warn', 'fail', 'error') AND unique_id LIKE 'test.%.elementary_%' ORDER BY 2"
)


def report(con: Connection) -> tuple[list[str], bool]:
    """O resumo da última verificação: fontes e carga, testes do dbt e anomalias dos marts.

    Devolve (linhas do relatório, há problema?).
    """
    lines: list[str] = []
    sources = con.execute(
        "SELECT status, source || '.' || dataset, check_name, detail, count(*), "
        "min(partition), max(partition) FROM metadata.source_checks WHERE status <> 'ok' AND id IN "
        "(SELECT max(id) FROM metadata.source_checks GROUP BY source, dataset, partition, check_name) "
        "GROUP BY ALL ORDER BY status DESC, 2, 3"
    ).fetchall()
    source_errors = sum(n for status, *_, n, _, _ in sources if status == "error")
    total = sum(n for *_, n, _, _ in sources)
    lines += [
        f"Fontes e carga (última verificação): {source_errors} erros, {total - source_errors} avisos",
    ]
    for status, name, check, detail, n, first, last in sources:
        years = (
            f" ({first} a {last})"
            if first is not None and first != last
            else (f" ({first})" if first else "")
        )
        lines.append(
            f"  [{status}] {name} ({check}): {detail}: {n} partições{years}"
            if n > 1
            else f"  [{status}] {name} ({check}): {detail}{years}"
        )
    failing = con.execute(
        "SELECT status, unique_id, failures FROM metadata.dbt_results "
        "WHERE run_id IN (SELECT max(id) FROM metadata.runs WHERE source = 'dbt' AND stage LIKE 'transform%' "
        "GROUP BY stage) "
        "AND status IN ('error', 'fail') ORDER BY 2"
    ).fetchall()
    lines += ["", f"Testes do dbt das últimas fases: {len(failing)} reprovados"]
    lines += [f"  [{s}] {uid} ({n})" for s, uid, n in failing]
    anomalies = con.execute(ANOMALIES).fetchall()
    lines += ["", f"Anomalias nos marts (Elementary): {len(anomalies)}"]
    lines += [f"  [{s}] {uid}: {(message or '')[:200]}" for s, uid, _, message in anomalies]
    return lines, bool(source_errors or failing or anomalies)


def html_report(settings: Settings) -> Path:
    """Gera o relatório HTML do Elementary (`edr report`, rodado por `uvx`, sem entrar nas dependências).

    O `edr` escreve no warehouse: o pipeline precisa estar parado e nenhuma conexão pode estar aberta.
    """
    uvx = shutil.which("uvx")
    if uvx is None:
        raise RuntimeError("uvx não encontrado: instale o uv (https://docs.astral.sh/uv/)")
    folder = settings.state_dir / "observabilidade"
    folder.mkdir(parents=True, exist_ok=True)
    file = folder / "report.html"
    command = [uvx, "--from", f"elementary-data[duckdb]=={ELEMENTARY}", "edr", "report"]
    command += ["--profiles-dir", str(DBT_DIR), "--file-path", str(file)]
    env = {**os.environ, "DADO_PUBLICO_WAREHOUSE_FILE": str(settings.warehouse.resolve())}
    subprocess.run(
        command, cwd=folder, env=env, check=True, capture_output=True
    )  # cwd: o edr cria `edr_target`
    return file


def notify(con: Connection) -> bool:
    """Manda o relatório por e-mail se houver problema e o SMTP estiver configurado. Nunca falha."""
    lines, failed = report(con)
    if not failed:
        return False
    try:
        return alert.send("Plataforma de dados: problemas nos dados", chr(10).join(lines))
    except (OSError, smtplib.SMTPException) as error:
        print(f"Alerta por e-mail não enviado: {error}")
        return False
