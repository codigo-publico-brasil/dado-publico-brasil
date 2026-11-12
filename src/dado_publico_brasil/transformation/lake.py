"""O lake publicado: raiz (R2 ou pasta local), conexão, manifesto, catálogo, versões, órfãos e docs.

O catálogo é um DuckDB, que o DuckDB não escreve no R2: sobe, e os órfãos saem, por requisições assinadas
(SigV4, `core/s3.py`).
"""

import json
import logging
import os
import re
import shutil
import time
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
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


def put_text(con: warehouse.Connection, root: str, key: str, text: str) -> None:
    """Grava um texto de uma linha em `root/key` (o COPY do DuckDB serve para o R2 e para a pasta local)."""
    if not r2():
        Path(root, key).parent.mkdir(parents=True, exist_ok=True)
    con.execute(
        f"COPY (SELECT ?) TO '{q(root)}/{key}' "
        "(FORMAT csv, HEADER false, QUOTE '', ESCAPE '', DELIMITER '\x01')",
        (text,),
    )


def put_file(root: str, key: str, file: Path) -> None:
    """Sobe (ou copia) um arquivo para `root/key`."""
    if r2():
        request("PUT", key, file)
    else:
        Path(root, key).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(file, Path(root, key))


def utcnow() -> datetime:
    return datetime.now(UTC)


def retention_months() -> int:
    """Meses de versões mensais com Parquet retidos (`DADO_PUBLICO_VERSOES_MESES`, padrão 12)."""
    return int(os.environ.get("DADO_PUBLICO_VERSOES_MESES", "12"))


def retention(con: warehouse.Connection, root: str) -> tuple[set[str], dict[str, set[str]]]:
    """Arquivos que as versões datadas citam: `(retidos, vencidos por versão)` (ADR 0052, retenção).

    Retém a versão dentro da janela de meses ou com `fixada.json`; só os arquivos que NENHUMA versão retida
    cita entram em `vencidos` (quem chama ainda os confere contra o manifesto raiz antes de apagar).
    """
    now = utcnow()
    fixed = {f.split("/")[-2] for f in glob(con, f"{root}/versoes/*/fixada.json")}
    kept: set[str] = set()
    cited: dict[str, set[str]] = {}
    for file in glob(con, f"{root}/versoes/*/manifesto.json"):
        name = file.split("/")[-2]
        files = {
            f["arquivo"]
            for t in read_manifest(con, file.rsplit("/", 1)[0]).get("tabelas", [])
            for f in t["arquivos"]
        }
        age = (
            (now.year - int(name[:4])) * 12 + now.month - int(name[5:7])
            if re.fullmatch(r"\d{4}-\d{2}", name)
            else 0
        )
        if name in fixed or age <= retention_months():  # nome fora do padrão: retém
            kept |= files
        else:
            cited[name] = files
    return kept, {v: files - kept for v, files in cited.items()}


def mark_removed(con: warehouse.Connection, root: str, versions: set[str]) -> None:
    """Marca no manifesto da versão vencida que os Parquet saíram (ela segue descrevendo e dando o hash)."""
    for v in sorted(versions):
        manifest = read_manifest(con, f"{root}/versoes/{v}")
        if manifest and "arquivos_removidos" not in manifest:
            manifest["arquivos_removidos"] = utcnow().isoformat(timespec="seconds")
            put_text(con, root, f"versoes/{v}/manifesto.json", json.dumps(manifest, ensure_ascii=True))


def fix(con: warehouse.Connection, root: str, version: str, doi: str) -> None:
    """Fixa a versão: `fixada.json` (DOI e data) a mantém, com os Parquet, até pedido de remoção."""
    manifest = read_manifest(con, f"{root}/versoes/{version}")
    if not manifest:
        raise ValueError(f"versão {version} não existe")
    if "arquivos_removidos" in manifest:
        raise ValueError(f"versão {version} já perdeu os Parquet: não há o que fixar")
    put_text(
        con,
        root,
        f"versoes/{version}/fixada.json",
        json.dumps({"doi": doi, "dt_fixacao": utcnow().isoformat(timespec="seconds")}),
    )


def delete_orphans(con: warehouse.Connection, root: str, patterns: set[str], keep: set[str]) -> int:
    """Apaga o que casa com `patterns` (relativos à raiz) e não está em `keep`; só padrões conhecidos."""
    orphans = sorted(
        {f for pattern in patterns for f in glob(con, f"{root}/{pattern}") if f[len(root) + 1 :] not in keep}
    )
    for f in orphans:
        if root.startswith("r2://"):
            request("DELETE", f[len(root) + 1 :])
        else:
            Path(f).unlink()
    return len(orphans)


_INT = ("INT", "INTEGER")


def _type(duck: str) -> str:
    """Tipo do Frictionless para o tipo do DuckDB (`any` se não houver correspondente exato)."""
    t = re.sub(r"\(.*", "", duck.upper())
    if t.endswith(_INT):
        return "integer"
    return {
        "VARCHAR": "string",
        "BOOLEAN": "boolean",
        "DATE": "date",
        "TIME": "time",
        "TIMESTAMP": "datetime",
        "TIMESTAMP WITH TIME ZONE": "datetime",
        "DOUBLE": "number",
        "FLOAT": "number",
        "DECIMAL": "number",
    }.get(t, "any")


def datapackage(manifest: dict[str, Any]) -> dict[str, Any]:
    """Descritor Frictionless Data Package (https://datapackage.org) gerado do manifesto, sem dado novo."""
    base = manifest["base"].rstrip("/")
    resources = []
    for t in manifest["tabelas"]:
        paths = [f"{base}/{f['arquivo']}" for f in t["arquivos"]]
        res: dict[str, Any] = {
            "name": f"{t['camada']}.{t['tabela']}".lower(),
            "path": paths[0] if len(paths) == 1 else paths,
            "format": "parquet",
            "mediatype": "application/vnd.apache.parquet",
            "description": t["descricao"],
            "schema": {
                "fields": [
                    {"name": c["nome"], "type": _type(c["tipo"]), "description": c["descricao"]}
                    for c in t["colunas"]
                ]
            },
        }
        if len(paths) == 1:
            res |= {"bytes": t["arquivos"][0]["bytes"], "hash": f"sha256:{t['arquivos'][0]['sha256']}"}
        if t.get("licenca"):
            res["licenses"] = [{"name": t["licenca"]}]
        resources.append(res)
    return {
        "name": "dado-publico-brasil",
        "title": "Dado Público Brasil",
        "version": manifest.get("versao") or manifest["id_execucao"],
        "created": manifest["dt_exportacao"],
        "id_execucao": manifest["id_execucao"],
        "versao_commit": manifest["versao_commit"],
        "homepage": "https://datalake.codigopublicobrasil.com.br",
        "licenses": [
            {
                "name": "CC-BY-4.0",
                "path": "https://creativecommons.org/licenses/by/4.0/",
                "title": "Dados curados; cada recurso cita a licença da fonte quando há",
            }
        ],
        "resources": resources,
    }


def snapshot(con: warehouse.Connection, settings: Settings, root: str) -> str | None:
    """Fixa a versão datada do mês (`versoes/AAAA-MM/`: catálogo, `datapackage.json` e manifesto por último).

    É o manifesto publicado agora, na primeira execução do mês; depois de gravada, nunca é reescrita. Os
    Parquet não são copiados: a versão os referencia e `retention` impede que sejam apagados. Devolve a versão
    criada, ou None se o mês já tem uma (ou não há manifesto).
    """
    manifest = read_manifest(con, root)
    if not manifest:
        return None
    version = utcnow().strftime("%Y-%m")
    folder = f"versoes/{version}"
    if read_manifest(con, f"{root}/{folder}"):
        return None
    manifest["versao"] = version
    catalog = settings.state_dir / "catalogo_versao.duckdb"
    write_catalog(manifest["tabelas"], catalog, manifest["base"], manifest)
    put_file(root, f"{folder}/catalogo.duckdb", catalog)
    catalog.unlink()
    put_text(con, root, f"{folder}/datapackage.json", json.dumps(datapackage(manifest), ensure_ascii=True))
    put_text(con, root, f"{folder}/manifesto.json", json.dumps(manifest, ensure_ascii=True))
    return version


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
