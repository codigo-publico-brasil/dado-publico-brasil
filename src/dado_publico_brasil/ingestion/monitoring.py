"""Monitoramento das fontes: a fonte respondeu? as colunas mudaram? o volume despencou?

Cada verificação grava uma linha em `metadata.source_checks` (status `ok`, `warn` ou `error`), que a
orquestração e a página de qualidade leem. Nada aqui interrompe a captura: o objetivo é saber que algo
quebrou, não parar o que ainda funciona. O frescor (idade do dado carregado) é medido pelo dbt.
"""

import fnmatch
import json
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

from dado_publico_brasil.core import runs
from dado_publico_brasil.core.warehouse import Connection
from dado_publico_brasil.ingestion import read
from dado_publico_brasil.ingestion.contract import Dataset, SourceContract

VOLUME_DROP = 0.8  # menos de 80% das linhas da carga anterior vira aviso


def record(
    con: Connection,
    source: str,
    dataset: str,
    partition: int | None,
    check: str,
    status: str,
    detail: str = "",
) -> None:
    con.execute(
        "INSERT INTO metadata.source_checks "
        "(checked_at, source, dataset, partition, check_name, status, detail) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (runs.now(), source, dataset, partition, check, status, detail),
    )


def check_header(
    con: Connection, contract: SourceContract, dataset: Dataset, partition: int | None, file: Path
) -> None:
    """Compara os campos do arquivo com o contrato e com a captura anterior do mesmo dataset e partição.

    Coluna do contrato ausente é erro em CSV (o layout mudou) e aviso em JSON (a API omite campo vazio, então
    ausente quer dizer vazio no arquivo todo). Nome antigo declarado em `aliases` vale como a coluna atual, e
    coluna em `optional` (só existe em anos recentes) pode faltar. A mudança de colunas só se mede contra o
    mesmo arquivo capturado antes: um ano antigo ter menos campos que o seguinte é a natureza do dado, não
    alerta.
    """
    header = read.fields(file, contract, dataset)
    source, name = contract.source, dataset.name
    if not header:  # sem registros não há o que comparar (o volume é medido à parte)
        record(con, source, name, partition, "schema", "ok", "arquivo sem registros")
        return
    present = set(header) | {new for old, new in dataset.aliases.items() if old in header}
    missing = [c for c in dataset.columns if c not in present and c not in dataset.optional]
    previous = con.execute(
        "SELECT detail FROM metadata.source_checks WHERE source = ? AND dataset = ? "
        "AND partition IS NOT DISTINCT FROM ? AND check_name = 'header' ORDER BY id DESC LIMIT 1",
        (source, name, partition),
    ).fetchone()
    old = json.loads(previous[0]) if previous else None
    changed = old is not None and set(old) != set(header)
    if missing:
        severity = "warn" if contract.format_of(name) == "json" else "error"
        record(con, source, name, partition, "schema", severity, f"colunas do contrato ausentes: {missing}")
    if changed:
        added, removed = sorted(set(header) - set(old or [])), sorted(set(old or []) - set(header))
        detail = f"colunas novas: {added}; removidas: {removed}"
        record(con, source, name, partition, "schema_mudou", "warn", detail)
    if not missing:
        record(con, source, name, partition, "schema", "ok")
    if not changed:
        record(con, source, name, partition, "schema_mudou", "ok")
    if old is None or changed:
        record(con, source, name, partition, "header", "ok", json.dumps(header))


def check_integrity(
    con: Connection,
    source: str,
    dataset: Dataset,
    partition: int | None,
    file: Path,
    url: str,
    expected_size: str | None = None,
    expected_format: str = "csv",
) -> bool:
    """Confere o arquivo recebido antes de virar captura.

    Não pode ser uma página HTML no lugar do arquivo; o tamanho bate com o `Content-Length` informado;
    nos pacotes `.zip`, o zip abre sem erro e tem os membros esperados.

    Devolve falso e registra `integridade` com erro (data e endereço). O arquivo fica no landing como
    evidência, mas não vira captura vigente, e a próxima execução tenta de novo.
    """
    problems: list[str] = []
    with file.open("rb") as f:
        start = f.read(512).lstrip().lower()
    if expected_format != "html" and start.startswith((b"<!doctype html", b"<html")):
        problems.append("o conteúdo é uma página HTML, não o arquivo esperado")
    if expected_size and expected_size.isdigit() and int(expected_size) != file.stat().st_size:
        problems.append(f"recebidos {file.stat().st_size} bytes, a fonte informou {expected_size}")
    if dataset.archive == "zip" and not problems:
        try:
            with zipfile.ZipFile(file) as archive:
                broken = archive.testzip()
                if broken:
                    problems.append(f"membro corrompido no zip: {broken}")
                elif not any(fnmatch.fnmatch(n, dataset.member) for n in archive.namelist()):
                    problems.append(f"nenhum membro {dataset.member} no zip")
        except zipfile.BadZipFile as error:
            problems.append(f"zip inválido: {error}")
    if problems:
        record(con, source, dataset.name, partition, "integridade", "error", f"{url}: {'; '.join(problems)}")
        return False
    record(con, source, dataset.name, partition, "integridade", "ok")
    return True


def check_volume(con: Connection, source: str, dataset: str, partition: int | None, rows: int) -> None:
    """Avisa se a carga trouxe muito menos linhas que a anterior do mesmo dataset e partição."""
    previous = con.execute(
        "SELECT rows_in FROM metadata.runs WHERE stage = 'load' AND source = ? AND dataset = ? "
        "AND year IS NOT DISTINCT FROM ? AND status = 'ok' ORDER BY id DESC LIMIT 1",
        (source, dataset, partition),
    ).fetchone()
    if previous and previous[0] and rows < VOLUME_DROP * previous[0]:
        record(con, source, dataset, partition, "volume", "warn", f"de {previous[0]} para {rows} linhas")
    else:
        record(con, source, dataset, partition, "volume", "ok", f"{rows} linhas")


def latest_status(con: Connection, source: str, dataset: str) -> tuple[str, list[str]]:
    """O pior estado (`error`, `warn` ou `ok`) de um dataset e os detalhes das verificações fora de `ok`.

    Cada verificação (por partição e nome) vale pelo registro mais recente: erro já corrigido não conta.
    """
    found = con.execute(
        "SELECT status, check_name, partition, detail FROM metadata.source_checks "
        "WHERE source = ? AND dataset = ? AND status <> 'ok' AND id IN ("
        "SELECT max(id) FROM metadata.source_checks WHERE source = ? AND dataset = ? "
        "GROUP BY partition, check_name) ORDER BY status DESC, check_name, partition",
        (source, dataset, source, dataset),
    ).fetchall()
    details = [f"[{s}] {name}{f' ({p})' if p is not None else ''}: {d}" for s, name, p, d in found]
    return ("error" if any(f[0] == "error" for f in found) else "warn" if found else "ok"), details


def check_removed(
    con: Connection, source: str, dataset: str, partition: int | None, table: str, capture: dict[str, Any]
) -> None:
    """Avisa se o raw guarda linhas de capturas anteriores do mesmo arquivo que a captura atual não traz.

    O `merge` do dlt não apaga: uma linha que a fonte removeu (ou, em dataset de chave por conteúdo, alterou)
    continua no raw com o id da captura antiga. Só se mede quando o arquivo já foi capturado antes.
    """
    older = "SELECT id FROM metadata.captures WHERE url = ? AND id <> ?"
    args = (capture["url"], capture["id"])
    if not con.execute(older, args).fetchone():
        return
    n = con.execute(f"SELECT count(*) FROM {table} WHERE _source_file_id IN ({older})", args).fetchone()
    count = int(n[0]) if n else 0
    detail = f"{count} linhas de capturas anteriores que a atual não traz (removidas ou alteradas pela fonte)"
    record(con, source, dataset, partition, "linhas_removidas", "warn" if count else "ok", detail)


def check_load(
    con: Connection, source: str, dataset: str, partition: int | None, stats: dict[str, int]
) -> None:
    """Registra o balanço da carga: o que foi lido, filtrado pelo `only`, carregado, rejeitado e em colisão.

    Linha rejeitada (sem valor na chave) e chave que junta linhas diferentes são perda de dado e valem erro. O
    filtro `only` da declaração fica no detalhe, para nunca ser invisível. Um registro por carga: o mais
    recente substitui o anterior no relatório.
    """
    lost = stats["rejected"] or stats["conflicting"]
    detail = (
        f"lidas {stats['read']}, filtradas pelo only {stats['filtered']}, carregadas {stats['loaded']}, "
        f"rejeitadas {stats['rejected']}, colisões de chave {stats['conflicting']}"
    )
    record(con, source, dataset, partition, "carga", "error" if lost else "ok", detail)


def errors_since(con: Connection, moment: datetime) -> int:
    """Quantas verificações com erro foram gravadas desde o momento dado."""
    row = con.execute(
        "SELECT COUNT(*) FROM metadata.source_checks WHERE status = 'error' AND checked_at >= ?",
        (moment.isoformat(timespec="seconds"),),
    ).fetchone()
    return int(row[0]) if row else 0
