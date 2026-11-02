"""Exporta o lakehouse público em Parquet (ADR 0035): staging de fonte, intermediate, marts e as capturas.

Lê o warehouse só para leitura e grava na raiz do lake: o bucket do R2 (`r2://bucket`, pelo `httpfs`
do DuckDB, sem cópia local) se DADO_PUBLICO_R2_* estiver completo; senão `<storage_root>/lake/` (dev):

    staging/<poder>/<esfera>/<fonte>/<modelo>    (a árvore de `sources/`; a fonte sai de `stg_<fonte>__...`)
    intermediate/<modelo>
    marts/<dominio>/<tabela>                     (domínio = pasta do modelo no dbt; sem as views `app_`)
    metadata/capturas

Cada tabela é `<caminho>.parquet` (um arquivo, ordenado pelo período se tiver `meta.particao`) ou, se tiver
`meta.particao` (expressão SQL do ano, declarada no dbt) e a estimativa passar de `max_bytes`,
`<caminho>/ano=AAAA/part-0.parquet`. Ano nulo é erro. Mais, na raiz:
    manifesto.json    arquivo, linhas, bytes, sha256, impressão, esquema, partição e descrições de cada tabela
    catalogo.duckdb   uma view por tabela (lista explícita de arquivos), com COMMENT de tabela e coluna

Idempotente e barato de repetir: cada tabela leva uma impressão digital do conteúdo, calculada no DuckDB numa
varredura (contagem, XOR dos hashes das linhas, que não depende da ordem, esquema e caminho). Se for igual à
do manifesto anterior (lido da raiz), a tabela é ignorada. Catálogo e manifesto são trocados por último; só
então se apagam os objetos órfãos sob os caminhos das tabelas (mudança de arquivo único para partição, tabela
removida). Nunca exporta `raw`, `identity` nem colunas de documento pessoal. O catálogo é um DuckDB, que o
DuckDB não escreve no R2: sobe, e os órfãos saem, por requisições assinadas (SigV4) da biblioteca padrão.
"""

import hashlib
import hmac
import json
import os
import re
import shutil
import urllib.request
import warnings
from contextlib import nullcontext
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote

import duckdb

from dado_publico_brasil.core import privado, runs, warehouse
from dado_publico_brasil.core.settings import DBT_DIR, SITE_DIR, SOURCES_DIR, Settings
from dado_publico_brasil.core.warehouse import scalar
from dado_publico_brasil.transformation import dbt, observability

LAYERS = ("staging", "intermediate", "marts")
EXTRA = (("metadata", "capturas"),)  # único lugar do nome da tabela de capturas
MEDALLION = {"staging": "prata", "intermediate": "prata", "marts": "ouro", "metadata": "bronze"}
PRIVATE_SOURCES = ("identity", "metadata")  # modelos `stg_identity__*` e `stg_metadata__*` não são de fonte
PERSONAL = re.compile(r"(^|_)(cpf|rg|titulo_eleitor|documento|nr_documento)(_|$)")
YEAR_COLUMN = "ano"
MAX_BYTES = 128 << 20  # estimativa acima disto, a tabela com `meta.particao` vira uma pasta por ano
SAMPLE_ROWS = 200_000  # linhas do COPY de amostra que mede os bytes por linha
MAX_KV_BYTES = 64 << 10  # teto prático do JSON de descrições no rodapé do Parquet
ROW_GROUP = 500_000  # entre 122.880 e 1 milhão de linhas por grupo
MEMORY_LIMIT = "4GB"  # a máquina do mantenedor tem 8 GB
ENV_URL = "DADO_PUBLICO_LAKE_URL"


def _q(text: str) -> str:
    return text.replace("'", "''")


def _r2() -> dict[str, str]:
    cfg = {**privado.credentials(), "BUCKET": os.environ.get("DADO_PUBLICO_R2_BUCKET", "")}
    return cfg if all(cfg.values()) and len(cfg) == 4 else {}


def _root(settings: Settings) -> str:
    """Raiz do lake: `r2://bucket` com o segredo completo, senão a pasta local."""
    cfg = _r2()
    return f"r2://{cfg['BUCKET']}" if cfg else (settings.storage_root / "lake").as_posix()


def _connect(settings: Settings, warehouse_file: bool) -> warehouse.Connection:
    """Conexão com limites de memória e, havendo segredo, acesso ao R2; o warehouse só para leitura."""
    con = warehouse.connect(settings, read_only=True) if warehouse_file else duckdb.connect()
    con.execute(f"SET memory_limit = '{MEMORY_LIMIT}'")
    con.execute(f"SET temp_directory = '{_q((settings.state_dir / 'duckdb_tmp').as_posix())}'")
    privado.secret(con)
    return con


def _relations(con: warehouse.Connection) -> list[tuple[str, str]]:
    """(esquema, nome) das tabelas e views a exportar, pela ordem das camadas."""
    marks = ",".join("?" * len(LAYERS))
    found = {
        (s, t)
        for s, t in con.execute(
            "SELECT schema_name, table_name FROM duckdb_tables() WHERE database_name = current_database() "
            f"AND schema_name IN ({marks}) UNION SELECT schema_name, view_name FROM duckdb_views() "
            f"WHERE database_name = current_database() AND NOT internal AND schema_name IN ({marks})",
            (*LAYERS, *LAYERS),
        ).fetchall()
        if not (s == "marts" and t.startswith("app_"))
        and not (s == "staging" and _source(t) in (None, *PRIVATE_SOURCES))
    }
    return sorted(found | set(EXTRA), key=lambda r: (LAYERS.index(r[0]) if r[0] in LAYERS else 9, r[1]))


def _source(model: str) -> str | None:
    m = re.match(r"stg_([a-z0-9]+)__", model)
    return m.group(1) if m else None


def _models(settings: Settings) -> dict[str, dict[str, Any]]:
    """Modelos do `manifest.json` do dbt por nome (pasta e `config.meta`); vazio se ainda não houver."""
    file = dbt.target_dir(settings) / "manifest.json"
    if not file.exists():
        return {}
    nodes = json.loads(file.read_text(encoding="utf-8"))["nodes"].values()
    return {n["name"]: n for n in nodes if n["resource_type"] == "model"}


def _domain(models: dict[str, dict[str, Any]], table: str) -> str:
    """Pasta do mart em `dbt/models/marts`: do manifesto, ou (sem ele) procurando o `.sql` na árvore."""
    if table in models:
        return str(models[table]["original_file_path"]).replace("\\", "/").split("/")[2]
    found = sorted((DBT_DIR / "models" / "marts").glob(f"*/{table}.sql"))
    if not found:
        raise ValueError(f"mart {table} sem pasta de domínio em dbt/models/marts")
    return found[0].parent.name


def _key(models: dict[str, dict[str, Any]], schema: str, table: str) -> str:
    """Caminho da tabela no lake, sem extensão: poder/esfera/fonte no staging, domínio nos marts."""
    if schema == "staging":
        found = sorted(SOURCES_DIR.glob(f"*/*/{_source(table)}.yml"))
        if not found:
            raise ValueError(f"{table}: sem sources/<poder>/<esfera>/{_source(table)}.yml")
        return f"staging/{found[0].parent.parent.name}/{found[0].parent.name}/{_source(table)}/{table}"
    if schema == "marts":
        return f"marts/{_domain(models, table)}/{table}"
    return f"{schema}/{table}"


def _describe(con: warehouse.Connection, schema: str, table: str) -> tuple[str, list[dict[str, str]]]:
    """Descrição da tabela e esquema (nome, tipo, descrição) sem as colunas pessoais, lidos do DuckDB."""
    comment = con.execute(
        "SELECT comment FROM duckdb_tables() WHERE database_name = current_database() AND schema_name = ? "
        "AND table_name = ? UNION ALL SELECT comment FROM duckdb_views() WHERE "
        "database_name = current_database() AND schema_name = ? AND view_name = ?",
        (schema, table, schema, table),
    ).fetchone()
    columns = con.execute(
        "SELECT column_name, data_type, comment FROM duckdb_columns() "
        "WHERE database_name = current_database() AND schema_name = ? AND table_name = ? "
        "ORDER BY column_index",
        (schema, table),
    ).fetchall()
    return (comment[0] if comment and comment[0] else ""), [
        {"nome": n, "tipo": t, "descricao": c or ""} for n, t, c in columns if not PERSONAL.search(n)
    ]


def _manifest(con: warehouse.Connection, root: str) -> dict[str, Any]:
    """O manifesto que está na raiz (vazio se ainda não houver)."""
    try:
        row = con.execute(f"SELECT content FROM read_text('{_q(root)}/manifesto.json')").fetchone()
    except duckdb.Error:
        return {}
    return json.loads(row[0]) if row else {}


def _files(con: warehouse.Connection, root: str, pattern: str) -> list[dict[str, Any]]:
    """Arquivo, linhas, bytes e SHA-256 dos Parquet que casam com `pattern`, lidos de onde estão."""
    found = con.execute(
        f"SELECT filename, size, sha256(content) FROM read_blob('{_q(root)}/{pattern}') ORDER BY 1"
    ).fetchall()
    return [
        {
            "arquivo": name.replace("\\", "/")[len(root) + 1 :],
            "linhas": con.execute(f"SELECT count(*) FROM read_parquet('{_q(name)}')").fetchone()[0],  # type: ignore[index]
            "bytes": size,
            "sha256": digest,
        }
        for name, size, digest in found
    ]


def _kv(meta: dict[str, str], key: str, description: str, columns: list[dict[str, str]]) -> dict[str, str]:
    """Metadados do rodapé do Parquet: os da execução, a descrição da tabela e `descricoes_colunas` (JSON)."""
    described: dict[str, str] = {}
    for c in columns:
        if (
            c["descricao"]
            and len(json.dumps({**described, c["nome"]: c["descricao"]}).encode()) <= MAX_KV_BYTES
        ):
            described[c["nome"]] = c["descricao"]
        elif c["descricao"]:
            warnings.warn(f"{key}: descricoes_colunas passa de {MAX_KV_BYTES} bytes; cortada", stacklevel=2)
            break
    return {**meta, "descricao": description, "descricoes_colunas": json.dumps(described, ensure_ascii=False)}


def _copy(con: warehouse.Connection, select: str, target: str, meta: dict[str, str], extra: str = "") -> None:
    """Um COPY direto no destino: ZSTD, dicionário ligado."""
    kv = ", ".join(f"{k}: '{_q(v)}'" for k, v in meta.items())
    con.execute(
        f"COPY ({select}) TO '{_q(target)}' (FORMAT parquet, COMPRESSION zstd, COMPRESSION_LEVEL 3, "
        f"ROW_GROUP_SIZE {ROW_GROUP}, KV_METADATA {{{kv}}}{extra})"
    )


def _estimate(
    con: warehouse.Connection, settings: Settings, select: str, rows: int, meta: dict[str, str]
) -> int:
    """Bytes comprimidos estimados: um COPY de amostra (as primeiras linhas) vezes linhas / amostra."""
    if not rows:
        return 0
    sample = settings.state_dir / "duckdb_tmp" / "amostra.parquet"
    sample.parent.mkdir(parents=True, exist_ok=True)
    _copy(con, f"{select} LIMIT {SAMPLE_ROWS}", sample.as_posix(), meta)
    size = sample.stat().st_size
    sample.unlink()
    return size * rows // min(rows, SAMPLE_ROWS)


def _glob(con: warehouse.Connection, pattern: str) -> list[str]:
    return [
        r[0].replace("\\", "/") for r in con.execute(f"SELECT file FROM glob('{_q(pattern)}')").fetchall()
    ]


def _delete_orphans(con: warehouse.Connection, root: str, keys: set[str], keep: set[str]) -> int:
    """Apaga o que há sob `keys` (`k.parquet`, `k/**`) e não está em `keep`; só prefixos conhecidos."""
    orphans = [
        f
        for key in sorted(keys)
        for f in _glob(con, f"{root}/{key}.parquet") + _glob(con, f"{root}/{key}/**")
        if f[len(root) + 1 :] not in keep
    ]
    for f in orphans:
        if root.startswith("r2://"):
            r2_request("DELETE", f[len(root) + 1 :])
        else:
            Path(f).unlink()
    return len(orphans)


def _catalog(entries: list[dict[str, Any]], file: Path, base: str, meta: dict[str, str]) -> None:
    """`catalogo.duckdb`: uma view por tabela com a lista explícita de arquivos (bucket público não lista)."""
    file.parent.mkdir(parents=True, exist_ok=True)
    file.unlink(missing_ok=True)
    cat = duckdb.connect(str(file))
    for schema in sorted({e["camada"] for e in entries} | {"metadata"}):
        cat.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")
    for e in entries:
        name = f'{e["camada"]}."{e["tabela"]}"'
        urls = ", ".join(f"'{_q(base.rstrip('/'))}/{f['arquivo']}'" for f in e["arquivos"])
        cat.execute(f"CREATE VIEW {name} AS SELECT * FROM read_parquet([{urls}], hive_partitioning = false)")
        if e["descricao"]:
            cat.execute(f"COMMENT ON VIEW {name} IS '{_q(e['descricao'])}'")
        for c in e["colunas"]:
            if c["descricao"]:
                cat.execute(f"COMMENT ON COLUMN {name}.\"{c['nome']}\" IS '{_q(c['descricao'])}'")
    cat.execute(
        "CREATE TABLE metadata.exportacao AS SELECT ? AS id_execucao, ? AS dt_exportacao, ? AS versao_commit",
        (meta["id_execucao"], meta["dt_exportacao"], meta["versao_commit"]),
    )
    cat.execute("COMMENT ON TABLE metadata.exportacao IS 'Execução do export que gerou o lake publicado.'")
    cat.close()


def r2_request(method: str, key: str, path: Path | None = None, content_type: str | None = None) -> None:
    """PUT (de um arquivo) ou DELETE assinado (SigV4) no R2: o que o COPY e o `glob` do DuckDB não fazem."""
    cfg = _r2()
    host = f"{cfg['ACCOUNT_ID']}.r2.cloudflarestorage.com"
    now = datetime.now(UTC)
    stamp, day = now.strftime("%Y%m%dT%H%M%SZ"), now.strftime("%Y%m%d")
    uri = f"/{cfg['BUCKET']}/{quote(key)}"
    signed = "host;x-amz-content-sha256;x-amz-date"
    canonical = (
        f"{method}\n{uri}\n\nhost:{host}\nx-amz-content-sha256:UNSIGNED-PAYLOAD\nx-amz-date:{stamp}\n\n"
        f"{signed}\nUNSIGNED-PAYLOAD"
    )
    scope = f"{day}/auto/s3/aws4_request"
    to_sign = f"AWS4-HMAC-SHA256\n{stamp}\n{scope}\n{hashlib.sha256(canonical.encode()).hexdigest()}"
    secret = ("AWS4" + cfg["SECRET_ACCESS_KEY"]).encode()
    for part in (day, "auto", "s3", "aws4_request"):
        secret = hmac.new(secret, part.encode(), hashlib.sha256).digest()
    signature = hmac.new(secret, to_sign.encode(), hashlib.sha256).hexdigest()
    headers = {
        "x-amz-content-sha256": "UNSIGNED-PAYLOAD",
        "x-amz-date": stamp,
        "Authorization": f"AWS4-HMAC-SHA256 Credential={cfg['ACCESS_KEY_ID']}/{scope}, "
        f"SignedHeaders={signed}, Signature={signature}",
    }
    if path:
        headers["Content-Length"] = str(path.stat().st_size)
    if content_type:
        headers["Content-Type"] = content_type
    with path.open("rb") if path else nullcontext() as body:
        request = urllib.request.Request(  # noqa: S310
            f"https://{host}{uri}", data=body, method=method, headers=headers
        )
        urllib.request.urlopen(request, timeout=3600).close()  # noqa: S310


def _index(settings: Settings) -> Path:
    """`site/index.html` com a ficha preenchida pelo `manifesto.json` (traço se não houver)."""
    con = _connect(settings, warehouse_file=False)
    try:
        manifest = _manifest(con, _root(settings))
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


def publish_docs(settings: Settings) -> list[str]:
    """Sobe ao R2 o dbt e o Elementary (`docs/`) e a página inicial do lake (`index.html`).

    Roda depois do `export`, com o warehouse livre (o dbt e o `edr` o abrem). Sem R2, não faz nada.
    """
    if not _r2():
        return []
    pages = {"dbt": dbt.static_docs(settings), "qualidade": observability.html_report(settings)}
    keys = {f"docs/{name}.html": file for name, file in pages.items()} | {"index.html": _index(settings)}
    for key, file in keys.items():
        r2_request("PUT", key, file, "text/html; charset=utf-8")
    return list(keys)


def _table(
    con: warehouse.Connection,
    settings: Settings,
    root: str,
    meta: dict[str, str],
    key: str,
    select: str,
    expr: str | None,
    description: str,
    columns: list[dict[str, str]],
    rows: int,
    max_bytes: int,
) -> list[dict[str, Any]]:
    """Grava a tabela (arquivo único ou pasta por ano) e devolve os arquivos; acrescenta `ano` às colunas."""
    target = f"{root}/{key}"
    if not root.startswith("r2://"):
        Path(target).parent.mkdir(parents=True, exist_ok=True)
    base = meta
    meta = _kv(base, key, description, columns)
    if expr and _estimate(con, settings, select, rows, meta) > max_bytes:
        source = select.split(" FROM ", 1)[1]
        has_year = any(c["nome"] == YEAR_COLUMN for c in columns)
        if has_year and expr.strip() != YEAR_COLUMN:
            raise ValueError(
                f"{key}: a tabela já tem uma coluna `{YEAR_COLUMN}`; declare `particao: {YEAR_COLUMN}`"
            )
        nulls = scalar(con, f"SELECT count(*) FROM {source} WHERE ({expr}) IS NULL")
        if nulls:
            raise ValueError(f"{key}: {nulls} linha(s) com ano nulo em `{expr}` (corrija a partição no dbt)")
        kind = scalar(con, f"SELECT typeof(({expr})) FROM {source} LIMIT 1")
        if not has_year:
            columns.append({"nome": YEAR_COLUMN, "tipo": kind, "descricao": f"Ano da partição: {expr}."})
            meta = _kv(base, key, description, columns)
        _copy(
            con,
            select if has_year else select.replace(" FROM ", f", ({expr}) AS {YEAR_COLUMN} FROM ", 1),
            target,
            meta,
            f", PARTITION_BY ({YEAR_COLUMN}), WRITE_PARTITION_COLUMNS true, FILENAME_PATTERN 'part-{{i}}', "
            "OVERWRITE_OR_IGNORE",
        )
        return _files(con, root, f"{key}/**/*.parquet")
    _copy(con, f"{select} ORDER BY ({expr})" if expr else select, f"{target}.parquet", meta)
    return _files(con, root, f"{key}.parquet")


def export(
    settings: Settings, base_url: str | None = None, max_bytes: int = MAX_BYTES, prune: bool = False
) -> dict[str, int]:
    """Exporta o lake para a raiz (R2 ou pasta local). Devolve tabelas, gravadas, ignoradas, órfãos, bytes.

    Recusa, sem apagar nem publicar nada, se faltar no warehouse uma tabela do manifesto anterior (warehouse
    errado ou incompleto); `prune=True` autoriza a retirada dela do lake.
    """
    base = base_url or os.environ.get(ENV_URL) or ""
    root = _root(settings)
    if _r2() and not base:
        raise ValueError(f"defina {ENV_URL} (URL pública do lake) para exportar ao R2 (veja .env.example)")
    now = datetime.now(UTC)
    meta = {
        "id_execucao": now.strftime("%Y%m%dT%H%M%SZ"),
        "dt_exportacao": now.isoformat(timespec="seconds"),
        "versao_commit": runs.code_version(),
    }
    models = _models(settings)
    entries: list[dict[str, Any]] = []
    written = ignored = size = 0
    con = _connect(settings, warehouse_file=True)
    try:
        old_entries = _manifest(con, root).get("tabelas", [])
        before = {(e["camada"], e["tabela"]): e for e in old_entries}
        touched = {e.get("caminho", f"{e['camada']}/{e['tabela']}") for e in old_entries}
        relations = _relations(con)
        missing = sorted(f"{c}.{t}" for c, t in before if (c, t) not in set(relations))
        if missing and not prune:
            raise ValueError(
                f"o warehouse não tem {len(missing)} tabela(s) do manifesto publicado "
                f"({', '.join(missing[:5])}{'...' if len(missing) > 5 else ''}); "
                "nada foi apagado nem publicado. "
                "Confira o warehouse ou use --prune para retirá-las do lake"
            )
        for schema, table in relations:
            description, columns = _describe(con, schema, table)
            if not columns:
                continue
            key = _key(models, schema, table)
            expr = models.get(table, {}).get("config", {}).get("meta", {}).get("particao")
            cols = ", ".join(f'"{c["nome"]}"' for c in columns)
            select = f'SELECT {cols} FROM {schema}."{table}"'
            rows, xor, total = con.execute(  # xor sozinho zera pares de linhas iguais; a soma não
                f"SELECT count(*), coalesce(bit_xor(hash(t)), 0), coalesce(sum(hash(t)::HUGEINT), 0) "
                f"FROM ({select}) t"
            ).fetchone()  # type: ignore[misc]
            names = [(c["nome"], c["tipo"], c["descricao"]) for c in columns]
            fingerprint = hashlib.sha256(
                f"{rows}:{xor}:{total}:{names}:{key}:{expr}:{description}".encode()
            ).hexdigest()
            old = before.get((schema, table))
            if old and old["impressao"] == fingerprint:
                files, columns = old["arquivos"], old["colunas"]
                ignored += 1
            else:
                files = _table(
                    con, settings, root, meta, key, select, expr, description, columns, rows, max_bytes
                )
                touched.add(key)
                written += 1
                size += sum(f["bytes"] for f in files)
            years = sorted({int(m[1]) for f in files if (m := re.search(r"/ano=(\d+)/", f["arquivo"]))})
            entries.append(
                {
                    "camada": schema,
                    "camada_medalhao": MEDALLION[schema],
                    "tabela": table,
                    "caminho": key,
                    "descricao": description,
                    "linhas": rows,
                    "impressao": fingerprint,
                    "particao": expr,
                    "ano": years or None,
                    "colunas": columns,
                    "arquivos": files,
                }
            )
        catalog = settings.state_dir / "catalogo.duckdb"
        _catalog(entries, catalog, base or root, meta)
        if _r2():
            r2_request("PUT", "catalogo.duckdb", catalog)
        else:
            shutil.copyfile(catalog, f"{root}/catalogo.duckdb")
        catalog.unlink()
        text = json.dumps(
            {**meta, "tabelas": entries}, ensure_ascii=True
        )  # compacto: uma linha, sem aspas soltas
        con.execute(
            f"COPY (SELECT ?) TO '{_q(root)}/manifesto.json' "
            "(FORMAT csv, HEADER false, QUOTE '', ESCAPE '', DELIMITER '\\x01')",
            (text,),
        )  # por último
        keep = {f["arquivo"] for e in entries for f in e["arquivos"]}
        orphans = _delete_orphans(con, root, touched, keep)  # só depois do manifesto novo
    finally:
        con.close()
    return {
        "tabelas": len(entries),
        "gravadas": written,
        "ignoradas": ignored,
        "orfaos": orphans,
        "bytes": size,
    }


def verify(settings: Settings, base_url: str | None = None) -> list[str]:
    """Lê o manifesto publicado e confere cada arquivo (existência, bytes e SHA-256). Devolve os problemas."""
    base = (base_url or os.environ.get(ENV_URL) or _root(settings)).rstrip("/")
    con = _connect(settings, warehouse_file=False)
    try:
        manifest = _manifest(con, base)
        if not manifest:
            return [f"sem manifesto em {base}"]
        found = []
        for f in (f for t in manifest["tabelas"] for f in t["arquivos"]):
            try:
                row = con.execute(
                    f"SELECT size, sha256(content) FROM read_blob('{_q(base)}/{f['arquivo']}')"
                ).fetchone()
            except duckdb.Error:
                row = None
            if not row:
                found.append(f"falta {f['arquivo']}")
            elif row != (f["bytes"], f["sha256"]):
                found.append(f"{f['arquivo']} difere do manifesto")
        return found
    finally:
        con.close()
