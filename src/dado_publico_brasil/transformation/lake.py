"""O lake publicado: raiz (R2 ou pasta local), conexão, manifesto, catálogo, órfãos e a página de docs.

O catálogo é um DuckDB, que o DuckDB não escreve no R2: sobe, e os órfãos saem, por requisições assinadas
(SigV4, `core/s3.py`).
"""

import json
import logging
import os
import time
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

import duckdb

from dado_publico_brasil.core import privado, s3, warehouse
from dado_publico_brasil.core.settings import SITE_DIR, Settings
from dado_publico_brasil.transformation import dbt, observability

logger = logging.getLogger(__name__)

MEMORY_LIMIT = os.environ.get(
    "DADO_PUBLICO_DUCKDB_MEMORY", "4GB"
)  # padrão para 8 GB de RAM; suba em máquina maior
ENV_URL = "DADO_PUBLICO_LAKE_URL"


def q(text: str) -> str:
    return text.replace("'", "''")


def say(text: str) -> None:
    logger.info(text)


@contextmanager
def phase(name: str) -> Iterator[None]:
    """Imprime o tempo da fase ao fim."""
    start = time.monotonic()
    try:
        yield
    finally:
        say(f"[{name}] {time.monotonic() - start:.1f}s")


def r2() -> dict[str, str]:
    """As quatro variáveis do R2, ou vazio (modo local). Pela metade falha: nunca vira local em silêncio."""
    cfg = {k: os.environ.get(f"DADO_PUBLICO_R2_{k}", "") for k in (*privado.KEYS, "BUCKET")}
    if all(cfg.values()):
        return cfg
    if any(cfg.values()) or os.environ.get(ENV_URL):
        raise ValueError(f"R2 incompleto: defina as quatro DADO_PUBLICO_R2_* ou nenhuma, e sem {ENV_URL}")
    return {}


def location(settings: Settings) -> str:
    """Raiz do lake: `r2://bucket` com o segredo completo, senão a pasta local."""
    cfg = r2()
    return f"r2://{cfg['BUCKET']}" if cfg else (settings.storage_root / "lake").as_posix()


def request(
    method: str,
    key: str,
    path: Path | None = None,
    content_type: str | None = None,
    headers: dict[str, str] | None = None,
) -> bytes:
    """PUT, DELETE ou GET assinado no bucket do R2 configurado (`core/s3.py`)."""
    return s3.request(r2(), method, key, path, content_type, headers)


def list_objects(prefix: str) -> dict[str, int]:
    """Chave e tamanho dos objetos do bucket sob `prefix`."""
    return s3.list_objects(r2(), prefix)


def connect(settings: Settings, warehouse_file: bool) -> warehouse.Connection:
    """Conexão com limites de memória e, havendo segredo, acesso ao R2; o warehouse só para leitura."""
    con = warehouse.connect(settings, read_only=True) if warehouse_file else duckdb.connect()
    con.execute(f"SET memory_limit = '{MEMORY_LIMIT}'")
    con.execute("SET preserve_insertion_order = false")  # COPY e varredura sem reter a ordem em memória
    con.execute(f"SET temp_directory = '{q((settings.state_dir / 'duckdb_tmp').as_posix())}'")
    privado.secret(con)
    return con


def read_manifest(con: warehouse.Connection, root: str) -> dict[str, Any]:
    """O manifesto que está na raiz (vazio se ainda não houver)."""
    try:
        row = con.execute(f"SELECT content FROM read_text('{q(root)}/manifesto.json')").fetchone()
    except duckdb.Error:
        return {}
    return json.loads(row[0]) if row else {}


def glob(con: warehouse.Connection, pattern: str) -> list[str]:
    return [r[0].replace("\\", "/") for r in con.execute(f"SELECT file FROM glob('{q(pattern)}')").fetchall()]


def delete_orphans(con: warehouse.Connection, root: str, keys: set[str], keep: set[str]) -> int:
    """Apaga o que há sob `keys` (`k.parquet`, `k/**`) e não está em `keep`; só prefixos conhecidos."""
    orphans = [
        f
        for key in sorted(keys)
        for f in glob(con, f"{root}/{key}.parquet") + glob(con, f"{root}/{key}/**")
        if f[len(root) + 1 :] not in keep
    ]
    for f in orphans:
        if root.startswith("r2://"):
            request("DELETE", f[len(root) + 1 :])
        else:
            Path(f).unlink()
    return len(orphans)


def write_catalog(entries: list[dict[str, Any]], file: Path, base: str, meta: dict[str, str]) -> None:
    """`catalogo.duckdb`: uma view por tabela com a lista explícita de arquivos (bucket público não lista)."""
    file.parent.mkdir(parents=True, exist_ok=True)
    file.unlink(missing_ok=True)
    cat = duckdb.connect(str(file))
    for schema in sorted({e["camada"] for e in entries} | {"metadata"}):
        cat.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")
    for e in entries:
        name = f'{e["camada"]}."{e["tabela"]}"'
        urls = ", ".join(f"'{q(base.rstrip('/'))}/{f['arquivo']}'" for f in e["arquivos"])
        cat.execute(f"CREATE VIEW {name} AS SELECT * FROM read_parquet([{urls}], hive_partitioning = false)")
        note = (
            f" ATENÇÃO: versão anterior, não atualizada nesta publicação ({e['excluida_por']})."
            if e.get("excluida_por")
            else ""
        )
        if e["descricao"] or note:
            cat.execute(f"COMMENT ON VIEW {name} IS '{q(e['descricao'] + note)}'")
        for c in e["colunas"]:
            if c["descricao"]:
                cat.execute(f"COMMENT ON COLUMN {name}.\"{c['nome']}\" IS '{q(c['descricao'])}'")
    cat.execute(
        "CREATE TABLE metadata.exportacao AS SELECT ? AS id_execucao, ? AS dt_exportacao, ? AS versao_commit",
        (meta["id_execucao"], meta["dt_exportacao"], meta["versao_commit"]),
    )
    cat.execute("COMMENT ON TABLE metadata.exportacao IS 'Execução do export que gerou o lake publicado.'")
    for col, desc in (
        ("id_execucao", "Identificador da execução do export que gerou o lake publicado."),
        ("dt_exportacao", "Instante (UTC) em que o export gerou o lake publicado."),
        (
            "versao_commit",
            "Commit do código que fez o export; termina em +dirty se havia alteração não commitada.",
        ),
    ):
        cat.execute(f"COMMENT ON COLUMN metadata.exportacao.{col} IS '{q(desc)}'")
    cat.close()


def index(settings: Settings) -> Path:
    """`site/index.html` com a ficha preenchida pelo `manifesto.json` (traço se não houver)."""
    con = connect(settings, warehouse_file=False)
    try:
        manifest = read_manifest(con, location(settings))
    finally:
        con.close()
    when = manifest.get("dt_exportacao", "")
    fields = {
        "n_tabelas": str(len(manifest["tabelas"])) if manifest else "—",
        "atualizado": datetime.fromisoformat(when).strftime("%d/%m/%Y") if when else "—",
        "id_execucao": manifest.get("id_execucao", "—"),
    }
    html = (SITE_DIR / "index.html").read_text(encoding="utf-8")
    for name, value in fields.items():
        html = html.replace("{{" + name + "}}", value)
    file = settings.state_dir / "index.html"
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(html, encoding="utf-8")
    return file


def situation(settings: Settings, limits: dict[tuple[str, str], int] | None = None) -> Path:
    """`situacao.html`: dias desde a última captura por dataset, lidos de `metadata.capturas`."""
    con = warehouse.connect(settings, read_only=True)
    try:
        html = observability.freshness_html(con, limits or {})
    finally:
        con.close()
    file = settings.state_dir / "situacao.html"
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(html, encoding="utf-8")
    return file


def publish_docs(settings: Settings, limits: dict[tuple[str, str], int] | None = None) -> list[str]:
    """Sobe ao R2 as páginas de `docs/`: dbt, Elementary, situação das capturas e a página inicial.

    Roda depois do `export`, com o warehouse livre (o dbt e o `edr` o abrem). Sem R2, não faz nada.
    """
    if not r2():
        return []
    pages = {
        "dbt": dbt.static_docs(settings),
        "qualidade": observability.html_report(settings),
        "situacao": situation(settings, limits),
    }
    keys = {f"docs/{name}.html": file for name, file in pages.items()} | {"docs/index.html": index(settings)}
    for key, file in keys.items():
        request("PUT", key, file, "text/html; charset=utf-8")
    return list(keys)
