"""Coleções de arquivos do export (ADR 0037): lista, envio e tabela de controle `arq_<nome>`."""

import json
import mimetypes
import shutil
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import yaml

from dado_publico_brasil.core import warehouse
from dado_publico_brasil.core.settings import SOURCES_DIR, Settings
from dado_publico_brasil.transformation import lake, tables

UPLOADS = 16  # envios simultâneos ao R2


CACHE_CONTROL = "public, max-age=86400, must-revalidate"  # caminho estável, conteúdo pode mudar
CONTROL_DESCRIPTION = "Arquivos da coleção %s, um por linha, com hash e a captura de origem (ADR 0037)."
CONTROL_COLUMNS = (
    ("caminho", "VARCHAR", "Caminho do arquivo relativo à pasta da coleção."),
    ("sha256_arquivo", "VARCHAR", "SHA-256 do arquivo publicado."),
    ("qtd_bytes", "BIGINT", "Tamanho do arquivo publicado, em bytes."),
    ("content_type", "VARCHAR", "Tipo de mídia do arquivo (Content-Type)."),
    (
        "fl_original",
        "BOOLEAN",
        "Verdadeiro se os bytes são idênticos ao arquivo capturado da fonte; falso se foram extraídos.",
    ),
    ("fonte", "VARCHAR", "Fonte oficial do arquivo."),
    ("id_captura", "BIGINT", "Captura do landing de onde o arquivo veio (o pacote, se foi extraído)."),
    ("dt_captura", "TIMESTAMP", "Instante da captura do arquivo ou do pacote de origem."),
    ("url_fonte", "VARCHAR", "URL oficial de onde o arquivo ou o pacote de origem foi capturado."),
    ("sha256_captura", "VARCHAR", "SHA-256 do arquivo capturado na fonte (o pacote, se foi extraído)."),
)


def collect(
    con: warehouse.Connection, settings: Settings, prune: bool = False
) -> dict[str, list[dict[str, Any]]]:
    """Arquivos a publicar por coleção (caminho no lake): datasets com `files.publish: true` no YAML.

    Os arquivos já foram materializados na carga (`ingestion/arquivos.py`) em `<pasta de dados>/arquivos/...`;
    aqui só se lê essa pasta e `metadata.arquivos` (hash e captura de origem). Arquivo registrado que não está
    no disco é erro (não encolhe o controle em silêncio), salvo `prune`.
    """
    found: dict[str, list[dict[str, Any]]] = {}
    for file in sorted(SOURCES_DIR.glob("*/*/*.yml")):
        data = yaml.safe_load(file.read_text(encoding="utf-8"))
        power, level, source = file.parent.parent.name, file.parent.name, data["source"]
        for colecao in sorted({d["files"]["collection"] for d in data["datasets"].values() if _published(d)}):
            wanted = [
                n
                for n, d in data["datasets"].items()
                if _published(d) and d["files"]["collection"] == colecao
            ]
            key = f"staging/{power}/{level}/{source}/arq_{colecao}"
            folder = settings.storage_root / "arquivos" / power / level / source / f"arq_{colecao}"
            found[key] = []
            for name, sha, size, original, capture, moment, url, sha_capture in con.execute(
                "SELECT a.caminho, a.sha256_arquivo, a.qtd_bytes, a.fl_original, c.id_captura, c.dt_captura, "
                "c.url, c.sha256 FROM metadata.arquivos a JOIN metadata.capturas c USING (id_captura) "
                f"WHERE a.fonte = ? AND a.colecao = ? AND a.dataset IN ({','.join('?' * len(wanted))}) "
                "ORDER BY a.caminho",
                (source, colecao, *wanted),
            ).fetchall():
                if not (folder / name).exists():
                    if prune:
                        continue
                    raise ValueError(
                        f"{key}/{name} está em metadata.arquivos mas falta em {folder} (pasta arquivos/ "
                        "incompleta?); nada foi publicado. Use --prune para retirá-lo do lake"
                    )
                found[key].append(
                    {
                        "caminho": name,
                        "sha256_arquivo": sha,
                        "qtd_bytes": size,
                        "content_type": mimetypes.guess_type(name)[0] or "application/octet-stream",
                        "fl_original": original,
                        "fonte": source,
                        "id_captura": capture,
                        "dt_captura": moment,
                        "url_fonte": url,
                        "sha256_captura": sha_capture,
                        "local": folder / name,
                    }
                )
    return found


def _published(dataset: dict[str, Any]) -> bool:
    return (dataset.get("files") or {}).get("publish") is True


def send(root: str, key: str, files: list[dict[str, Any]], known: dict[str, str]) -> tuple[int, int]:
    """Grava no destino (R2 ou pasta local) só os arquivos que faltam ou mudaram em relação ao controle.

    Devolve (enviados, já no destino). Retomável: o arquivo novo (fora do controle) cuja chave já existe no
    destino com o mesmo tamanho veio de um envio interrompido e não é reenviado: o PUT leva o SHA-256 e o R2
    recusa corpo que não confere. O arquivo que mudou (já no controle) sempre é reenviado: o tamanho não
    prova o conteúdo. Só lista o destino se houver pendentes. O envio no R2 é paralelo (`UPLOADS` conexões).
    """
    pending = [f for f in files if known.get(f["caminho"]) != f["sha256_arquivo"]]
    if not pending:
        return 0, 0
    r2 = root.startswith("r2://")
    if r2:
        have = {k[len(key) + 1 :]: n for k, n in lake.list_objects(f"{key}/").items()}
    else:
        have = {
            p.relative_to(Path(root, key)).as_posix(): p.stat().st_size
            for p in Path(root, key).rglob("*")
            if p.is_file()
        }
    todo = [f for f in pending if f["caminho"] in known or have.get(f["caminho"]) != f["qtd_bytes"]]

    def put(f: dict[str, Any]) -> None:
        target = f"{key}/{f['caminho']}"
        if r2:
            lake.request("PUT", target, f["local"], f["content_type"], {"Cache-Control": CACHE_CONTROL})
        else:
            Path(root, target).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(f["local"], Path(root, target))

    with ThreadPoolExecutor(UPLOADS if r2 else 1) as pool:
        list(pool.map(put, todo))  # `list` propaga a primeira falha
    return len(todo), len(pending) - len(todo)


def control(
    con: warehouse.Connection,
    settings: Settings,
    root: str,
    meta: dict[str, str],
    key: str,
    files: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], str]:
    """Grava `arq_<nome>.parquet` (a lista dos arquivos) e devolve os arquivos do Parquet e a descrição."""
    description = CONTROL_DESCRIPTION % key.rsplit("/", 1)[1]
    columns = [{"nome": n, "tipo": t, "descricao": d} for n, t, d in CONTROL_COLUMNS]
    nl = chr(10)
    ndjson = settings.state_dir / "duckdb_tmp" / "controle.ndjson"
    ndjson.parent.mkdir(parents=True, exist_ok=True)
    ndjson.write_text(
        nl.join(json.dumps({k: v for k, v in f.items() if k != "local"}, default=str) for f in files),
        encoding="utf-8",
    )
    ddl = ", ".join(f"{n} {t}" for n, t, _ in CONTROL_COLUMNS)
    types = ", ".join(f"{n}: '{t}'" for n, t, _ in CONTROL_COLUMNS)
    con.execute(f"CREATE OR REPLACE TEMP TABLE controle ({ddl})")
    if files:
        con.execute(
            f"INSERT INTO controle SELECT * FROM read_json('{lake.q(ndjson.as_posix())}', "
            f"format = 'newline_delimited', columns = {{{types}}})"
        )
    ndjson.unlink()
    select = "SELECT * FROM controle ORDER BY caminho"
    return tables.write_table(
        con, settings, root, meta, key, select, None, description, columns, len(files), tables.MAX_BYTES
    ), description
