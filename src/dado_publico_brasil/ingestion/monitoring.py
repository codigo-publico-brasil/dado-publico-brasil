"""Monitoramento das fontes: a fonte respondeu? as colunas mudaram? o volume despencou?

Cada verificação grava uma linha em `metadata.fontes_verificacoes` (status `ok`, `warn` ou `error`), que a
orquestração e a página de qualidade leem. Nada aqui interrompe a captura: o objetivo é saber que algo
quebrou, não parar o que ainda funciona. O frescor (idade do dado carregado) é medido pelo dbt.
"""

import fnmatch
import json
import zipfile
from datetime import datetime
from pathlib import Path

from dado_publico_brasil.core import runs
from dado_publico_brasil.core.warehouse import Connection
from dado_publico_brasil.ingestion import read
from dado_publico_brasil.ingestion.contract import Dataset, SourceContract, Tolerance

VOLUME_DROP = 0.8  # menos de 80% das linhas da carga anterior vira aviso


def record(
    con: Connection,
    source: str,
    dataset: str,
    partition: int | None,
    check: str,
    status: str,
    detail: str = "",
    *,
    cd_status_http: int | None = None,
    tipo: str | None = None,
    bytes_esperados: int | None = None,
    bytes_recebidos: int | None = None,
    linhas: int | None = None,
) -> None:
    """Grava uma verificação. O `detail` é o texto para gente; quem decide algo lê as colunas próprias."""
    con.execute(
        "INSERT INTO metadata.fontes_verificacoes (dt_verificacao, fonte, dataset, particao, verificacao, "
        "resultado, detalhe, cd_status_http, tipo_ocorrencia, qtd_bytes_esperados, qtd_bytes_recebidos, "
        "qtd_linhas) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (runs.now(), source, dataset, partition, check, status, detail, cd_status_http, tipo)
        + (bytes_esperados, bytes_recebidos, linhas),
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
        "SELECT detalhe FROM metadata.fontes_verificacoes WHERE fonte = ? AND dataset = ? "
        "AND particao IS NOT DISTINCT FROM ? AND verificacao = 'header' ORDER BY id_verificacao DESC LIMIT 1",
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
    kinds: list[str] = []
    size = file.stat().st_size
    with file.open("rb") as f:
        start = f.read(512).lstrip().lower()
    if expected_format != "html" and start.startswith((b"<!doctype html", b"<html")):
        problems.append("o conteúdo é uma página HTML, não o arquivo esperado")
        kinds.append("html_no_lugar")
    divergent = bool(expected_size and expected_size.isdigit() and int(expected_size) != size)
    if divergent:
        problems.append(f"recebidos {size} bytes, a fonte informou {expected_size}")
        kinds.append("tamanho_divergente")
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
            kinds.append("zip_invalido")
    if problems:
        record(
            con,
            source,
            dataset.name,
            partition,
            "integridade",
            "error",
            f"{url}: {'; '.join(problems)}",
            tipo=kinds[0],
            bytes_esperados=int(expected_size) if divergent and expected_size else None,
            bytes_recebidos=size if divergent else None,
        )
        return False
    record(con, source, dataset.name, partition, "integridade", "ok")
    return True


def check_volume(con: Connection, source: str, dataset: str, partition: int | None, rows: int) -> None:
    """Avisa se a carga trouxe muito menos linhas que a anterior (erro se não trouxe nenhuma)."""
    previous = con.execute(
        "SELECT qtd_linhas_entrada FROM metadata.execucoes WHERE etapa = 'load' AND fonte = ? AND "
        "dataset = ? "
        "AND particao IS NOT DISTINCT FROM ? AND resultado = 'ok' ORDER BY id_execucao DESC LIMIT 1",
        (source, dataset, partition),
    ).fetchone()
    if previous and previous[0] and rows < VOLUME_DROP * previous[0]:
        severity = "error" if rows == 0 else "warn"  # 0 linhas onde havia: carga falha
        record(
            con,
            source,
            dataset,
            partition,
            "volume",
            severity,
            f"de {previous[0]} para {rows} linhas",
            linhas=rows,
        )
    else:
        record(con, source, dataset, partition, "volume", "ok", f"{rows} linhas", linhas=rows)


def latest_status(con: Connection, source: str, dataset: str) -> tuple[str, list[str]]:
    """O pior estado (`error`, `warn` ou `ok`) de um dataset e os detalhes das verificações fora de `ok`.

    Cada verificação (por partição e nome) vale pelo registro mais recente: erro já corrigido não conta.
    """
    found = con.execute(
        "SELECT resultado, verificacao, particao, detalhe FROM metadata.fontes_verificacoes "
        "WHERE fonte = ? AND dataset = ? AND resultado <> 'ok' AND id_verificacao IN ("
        "SELECT max(id_verificacao) FROM metadata.fontes_verificacoes WHERE fonte = ? AND dataset = ? "
        "GROUP BY particao, verificacao) ORDER BY resultado DESC, verificacao, particao",
        (source, dataset, source, dataset),
    ).fetchall()
    details = [f"[{s}] {name}{f' ({p})' if p is not None else ''}: {d}" for s, name, p, d in found]
    return ("error" if any(f[0] == "error" for f in found) else "warn" if found else "ok"), details


def check_removed(con: Connection, source: str, dataset: str, partition: int | None, count: int) -> None:
    """Avisa se a captura anterior do mesmo arquivo tinha linhas que a atual não traz.

    No `merge`, a pasta da captura antiga sai do raw quando a nova entra, então a linha que a fonte removeu
    (ou, em dataset de chave por conteúdo, alterou) deixa o raw; `count` é medido antes de apagar (o loader).
    Só se mede quando o arquivo já foi capturado antes.
    """
    detail = f"{count} linhas de capturas anteriores que a atual não traz (removidas ou alteradas pela fonte)"
    record(
        con, source, dataset, partition, "linhas_removidas", "warn" if count else "ok", detail, linhas=count
    )


def check_load(
    con: Connection,
    source: str,
    dataset: str,
    partition: int | None,
    stats: dict[str, int],
    tolerance: Tolerance | None = None,
) -> None:
    """Registra o balanço da carga: o que foi lido, filtrado pelo `only`, carregado, rejeitado e em colisão.

    Linha rejeitada (sem valor na chave) e chave que junta linhas diferentes são perda de dado e valem erro. O
    filtro `only` da declaração fica no detalhe, para nunca ser invisível. Um registro por carga: o mais
    recente substitui o anterior no relatório. Com `tolerated_rejects` declarada para a partição, rejeição
    até o limite (e sem colisão) vira aviso com a justificativa no detalhe; acima do limite volta a ser erro.
    """
    lost = stats["rejected"] or stats["conflicting"]
    tolerated = bool(tolerance and lost and not stats["conflicting"] and stats["rejected"] <= tolerance.limit)
    detail = (
        f"lidas {stats['read']}, filtradas pelo only {stats['filtered']}, carregadas {stats['loaded']}, "
        f"rejeitadas {stats['rejected']}, colisões de chave {stats['conflicting']}"
        + (f", substituídas de versões anteriores {stats['replaced']}" if stats.get("replaced") else "")
    )
    if tolerated and tolerance:
        detail += f"; tolerada: {tolerance.reason}"
    record(
        con,
        source,
        dataset,
        partition,
        "carga",
        "warn" if tolerated else "error" if lost else "ok",
        detail,
        linhas=stats["loaded"],
    )


def errors_since(con: Connection, moment: datetime) -> int:
    """Quantas verificações com erro foram gravadas desde o momento dado."""
    row = con.execute(
        "SELECT COUNT(*) FROM metadata.fontes_verificacoes WHERE resultado = 'error' AND dt_verificacao >= ?",
        (moment.isoformat(timespec="seconds"),),
    ).fetchone()
    return int(row[0]) if row else 0
