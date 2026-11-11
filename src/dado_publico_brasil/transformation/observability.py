"""Relatório de saúde dos dados (ADR 0018) e alerta por e-mail.

Reúne o que as camadas de verificação já gravaram em `metadata`: o monitor das fontes e o balanço de cada
carga (`fontes_verificacoes`), os testes do dbt e as anomalias que o Elementary detecta nos marts (volume,
colunas que mudam, nulos). Nada aqui interrompe o pipeline: `dado-publico observe` resume e falha (código de
saída 1) se houver problema, e `notify` manda o resumo por e-mail quando há.
"""

import logging
import os
import re
import shutil
import smtplib
import subprocess
from pathlib import Path

from dado_publico_brasil.core import alert
from dado_publico_brasil.core.settings import DBT_DIR, Settings
from dado_publico_brasil.core.warehouse import Connection
from dado_publico_brasil.transformation import branding, health

logger = logging.getLogger(__name__)

ELEMENTARY = "0.26.1"  # a mesma versão do pacote dbt em dbt/packages.yml

ANOMALIES = (
    "SELECT resultado, id_no, qtd_falhas, mensagem FROM metadata.testes_resultados WHERE id_execucao = "
    "(SELECT max(id_execucao) FROM metadata.execucoes WHERE etapa = 'transform_post' AND fonte = 'dbt') "
    "AND resultado IN ('warn', 'fail', 'error') AND id_no LIKE 'test.%.elementary_%' ORDER BY 2"
)


def report(con: Connection, limits: dict[tuple[str, str], int] | None = None) -> tuple[list[str], bool]:
    """O resumo da última verificação: fontes e carga, capturas velhas, testes do dbt e anomalias dos marts.

    `limits` diz a idade máxima, em dias, da última verificação de cada (fonte, dataset); quem conhece os
    contratos (a orquestração) o monta. Sem ele, a checagem de captura velha não roda.
    Devolve (linhas, há problema?).
    """
    lines: list[str] = []
    sources = con.execute(
        "SELECT resultado, fonte || '.' || dataset, verificacao, detalhe, count(*), "
        "min(particao), max(particao) FROM metadata.fontes_verificacoes WHERE resultado <> 'ok' AND "
        "id_verificacao IN "
        "(SELECT max(id_verificacao) FROM metadata.fontes_verificacoes GROUP BY fonte, dataset, "
        "particao, verificacao) "
        "GROUP BY ALL ORDER BY resultado DESC, 2, 3"
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
    stale = stale_captures(con, limits or {})
    lines += ["", f"Capturas velhas: {len(stale)}"]
    lines += [f"  [erro] {line}" for line in stale]
    failing = con.execute(
        "SELECT resultado, id_no, qtd_falhas FROM metadata.testes_resultados "
        "WHERE id_execucao IN (SELECT max(id_execucao) FROM metadata.execucoes WHERE fonte = 'dbt' AND "
        "etapa LIKE 'transform%' "
        "GROUP BY etapa) "
        "AND resultado IN ('error', 'fail') ORDER BY 2"
    ).fetchall()
    lines += ["", f"Testes do dbt das últimas fases: {len(failing)} reprovados"]
    lines += [f"  [{s}] {uid} ({n})" for s, uid, n in failing]
    anomalies = con.execute(ANOMALIES).fetchall()
    lines += ["", f"Anomalias nos marts (Elementary): {len(anomalies)}"]
    lines += [f"  [{s}] {uid}: {(message or '')[:200]}" for s, uid, _, message in anomalies]
    lines += ["", *health.lines(con)]
    return lines, bool(source_errors or stale or failing or anomalies)


def stale_captures(con: Connection, limits: dict[tuple[str, str], int]) -> list[str]:
    """Datasets cuja última verificação é mais velha que o limite (ou que nunca foram capturados).

    Usa `dt_verificacao`, que a pipeline atualiza a cada verificação da fonte mesmo quando o arquivo não
    mudou: se ele para de andar, a pipeline parou ou a fonte deixou de responder.
    """
    problems: list[str] = []
    for (source, dataset), limit in sorted(limits.items()):
        row = con.execute(
            "SELECT date_diff('day', max(dt_verificacao), now() AT TIME ZONE 'UTC') "
            "FROM metadata.capturas WHERE fonte = ? AND dataset = ?",
            (source, dataset),
        ).fetchone()
        age = None if row is None else row[0]
        if age is None:
            problems.append(f"{source}.{dataset}: nunca capturado (limite de {limit} dias)")
        elif age > limit:
            problems.append(f"{source}.{dataset}: última verificação há {age} dias (limite de {limit})")
    return problems


CLOUD_ITEM = re.compile(
    r'\{key:"[^"]+",path:"[^"]*",label:"[^"]+",description:"[^"]*",icon:[^,]+,\{\}\),isSaasPage:!0,tooltip:"[^"]*"\},?'
)
EMPTY_GROUP = re.compile(r',(?:"[A-Z &]+"|[A-Z]+):\[\]')
# o relatório só carrega o que é do próprio HTML: sem scripts nem requisições de terceiros (estatística, GTM)
CSP = "script-src 'unsafe-inline' 'unsafe-eval' blob:; worker-src blob:; connect-src 'self'"


def prune_report(html: str) -> str:
    """Tira do menu as páginas do Elementary Cloud (`isSaasPage`), que aqui só levam a anúncio."""
    html, removed = CLOUD_ITEM.subn("", html)
    if not removed:
        raise ValueError("menu do relatório sem itens do Elementary Cloud: o Elementary mudou o formato")
    html = EMPTY_GROUP.sub("", html)
    meta = f'<meta http-equiv="Content-Security-Policy" content="{CSP}">'
    return html.replace("<head>", "<head>" + meta, 1)


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
    command += ["--project-name", "Dado Público Brasil", "--disable-samples", "true"]
    command += ["--exclude-elementary-models", "true", "--config-dir", str(DBT_DIR / "edr")]
    env = {**os.environ, "DADO_PUBLICO_WAREHOUSE_FILE": str(settings.warehouse.resolve())}
    done = subprocess.run(  # cwd: o edr cria `edr_target`
        command, cwd=folder, env=env, check=False, capture_output=True, text=True, errors="replace"
    )
    if done.returncode:
        raise RuntimeError(f"edr report falhou ({done.returncode}): {(done.stderr or done.stdout)[-2000:]}")
    html = prune_report(file.read_text(encoding="utf-8"))
    file.write_text(branding.apply(html, "Dado Público Brasil · Qualidade dos dados"), encoding="utf-8")
    return file


def notify(con: Connection, limits: dict[tuple[str, str], int] | None = None) -> bool:
    """Manda o relatório por e-mail se houver problema e o SMTP estiver configurado. Nunca falha."""
    lines, failed = report(con, limits)
    if not failed:
        return False
    try:
        return alert.send("Plataforma de dados: problemas nos dados", chr(10).join(lines))
    except (OSError, smtplib.SMTPException) as error:
        logger.warning("Alerta por e-mail não enviado: %s", error)
        return False
