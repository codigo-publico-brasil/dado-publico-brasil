"""Tabelas do export: o que publicar (camadas, partição), o que barrar, a impressão digital e o Parquet."""

import hashlib
import json
import re
import time
import warnings
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from dado_publico_brasil.core import runs, warehouse
from dado_publico_brasil.core.settings import DBT_DIR, REGISTRY_ALIAS, SOURCES_DIR, Settings
from dado_publico_brasil.core.warehouse import scalar
from dado_publico_brasil.transformation import dbt, lake

LAYERS = ("staging", "intermediate", "marts")
# `metadata` publicada (ADR 0054, #279): as capturas, o histórico dos testes e as verificações das fontes
EXTRA = (("metadata", "capturas"), ("metadata", "fontes_verificacoes"), ("metadata", "testes_resultados"))
MEDALLION = {"staging": "prata", "intermediate": "prata", "marts": "ouro", "metadata": "bronze"}
PRIVATE_SOURCES = ("identity", "metadata")  # modelos `stg_identity__*` e `stg_metadata__*` não são de fonte
PERSONAL = re.compile(r"(^|_)(cpf|rg|titulo_eleitor|documento|nr_documento)(_|$)")
YEAR_COLUMN = "ano"
MAX_BYTES = 128 << 20  # estimativa acima disto, a tabela com `meta.particao` vira uma pasta por ano
SAMPLE_ROWS = 200_000  # linhas do COPY de amostra que mede os bytes por linha
MAX_KV_BYTES = 64 << 10  # teto prático do JSON de descrições no rodapé do Parquet
ROW_GROUP = 500_000  # entre 122.880 e 1 milhão de linhas por grupo


FINGERPRINTS = (
    4  # impressões digitais simultâneas (cursores só de leitura; o DuckDB já paraleliza cada varredura)
)


DB = f"database_name IN (current_database(), '{REGISTRY_ALIAS}')"  # o warehouse e o registry


def relations(con: warehouse.Connection) -> list[tuple[str, str]]:
    """(esquema, nome) das tabelas e views a exportar, pela ordem das camadas."""
    marks = ",".join("?" * len(LAYERS))
    found = {
        (s, t)
        for s, t in con.execute(
            f"SELECT schema_name, table_name FROM duckdb_tables() WHERE {DB} "
            f"AND schema_name IN ({marks}) UNION SELECT schema_name, view_name FROM duckdb_views() "
            f"WHERE {DB} AND NOT internal AND schema_name IN ({marks})",
            (*LAYERS, *LAYERS),
        ).fetchall()
        if not (s == "staging" and _source(t) in (None, *PRIVATE_SOURCES))
    }
    return sorted(found | set(EXTRA), key=lambda r: (LAYERS.index(r[0]) if r[0] in LAYERS else 9, r[1]))


def _source(model: str) -> str | None:
    m = re.match(r"stg_([a-z0-9]+)__", model)
    return m.group(1) if m else None


def licenca(key: str) -> str | None:
    """Licença do YAML da fonte de uma tabela de staging (`staging/<poder>/<esfera>/<fonte>/...`)."""
    parts = key.split("/")
    file = SOURCES_DIR.joinpath(*parts[1:4]).with_suffix(".yml") if parts[0] == "staging" else None
    if file is None or not file.exists():
        return None  # intermediate e marts misturam fontes: sem licença única
    return (
        str(licenca) if (licenca := yaml.safe_load(file.read_text(encoding="utf-8")).get("license")) else None
    )


def models(settings: Settings) -> dict[str, dict[str, Any]]:
    """Modelos do `manifest.json` do dbt por nome (pasta e `config.meta`); vazio se ainda não houver."""
    file = dbt.target_dir(settings) / "manifest.json"
    if not file.exists():
        return {}
    nodes = json.loads(file.read_text(encoding="utf-8"))["nodes"].values()
    return {n["name"]: n for n in nodes if n["resource_type"] == "model"}


def domain(models: dict[str, dict[str, Any]], table: str) -> str:
    """Pasta do mart em `dbt/models/marts`: do manifesto, ou (sem ele) procurando o `.sql` na árvore."""
    if table in models:
        return str(models[table]["original_file_path"]).replace("\\", "/").split("/")[2]
    found = sorted((DBT_DIR / "models" / "marts").glob(f"*/{table}.sql"))
    if not found:
        if (DBT_DIR / "seeds" / "marts" / f"{table}.csv").exists():
            return "referencia"  # tabela de referência curada à mão (seed): não tem pasta de modelo
        raise ValueError(f"mart {table} sem pasta de domínio em dbt/models/marts")
    return found[0].parent.name


def table_path(models: dict[str, dict[str, Any]], schema: str, table: str) -> str:
    """Caminho da tabela no lake, sem extensão: poder/esfera/fonte no staging, domínio nos marts."""
    if schema == "staging":
        found = sorted(SOURCES_DIR.glob(f"*/*/{_source(table)}.yml"))
        if not found:
            raise ValueError(f"{table}: sem sources/<poder>/<esfera>/{_source(table)}.yml")
        return f"staging/{found[0].parent.parent.name}/{found[0].parent.name}/{_source(table)}/{table}"
    if schema == "marts":
        return f"marts/{domain(models, table)}/{table}"
    return f"{schema}/{table}"


def _describe(con: warehouse.Connection, schema: str, table: str) -> tuple[str, list[dict[str, str]]]:
    """Descrição da tabela e esquema (nome, tipo, descrição) sem as colunas pessoais, lidos do DuckDB."""
    comment = con.execute(
        f"SELECT comment FROM duckdb_tables() WHERE {DB} AND schema_name = ? "
        "AND table_name = ? UNION ALL SELECT comment FROM duckdb_views() WHERE "
        f"{DB} AND schema_name = ? AND view_name = ?",
        (schema, table, schema, table),
    ).fetchone()
    columns = con.execute(
        "SELECT column_name, data_type, comment FROM duckdb_columns() "
        f"WHERE {DB} AND schema_name = ? AND table_name = ? "
        "ORDER BY column_index",
        (schema, table),
    ).fetchall()
    return (comment[0] if comment and comment[0] else ""), [
        {"nome": n, "tipo": t, "descricao": c or ""} for n, t, c in columns if not PERSONAL.search(n)
    ]


FAILED = ("error", "fail", "runtime error", "skipped")  # resultados do dbt que impedem a publicação nova


def blocked(con: warehouse.Connection, settings: Settings) -> dict[tuple[str, str], str]:
    """Tabelas que NÃO podem ser publicadas agora, com o motivo (ADR 0046).

    Lê o resultado de cada nó do dbt na última execução de cada fase (`metadata.testes_resultados`) e o
    manifesto: o modelo que falhou ou foi pulado (porque uma entrada a montante falhou) e o modelo testado por
    um teste reprovado (`attached_node`; teste singular: todos os modelos de que depende). Sem manifesto ou
    sem execução registrada, nada é barrado."""
    file = dbt.target_dir(settings) / "manifest.json"
    if not file.exists():
        return {}
    nodes = json.loads(file.read_text(encoding="utf-8"))["nodes"]
    found = con.execute(
        "SELECT id_no, resultado FROM metadata.testes_resultados "
        "WHERE tipo <> 'freshness' AND id_execucao IN "
        "(SELECT max(id_execucao) FROM metadata.execucoes WHERE fonte = 'dbt' AND etapa LIKE 'transform%' "
        f"GROUP BY etapa) AND resultado IN ({','.join('?' * len(FAILED))}) ORDER BY id_no",
        FAILED,
    ).fetchall()
    out: dict[tuple[str, str], str] = {}
    for unique_id, result in found:
        node = nodes.get(unique_id)
        if not node:
            continue
        if node["resource_type"] == "model":
            targets, reason = [node], f"modelo {node['name']}: {result}"
        elif node["resource_type"] == "test" and result != "skipped":
            attached = node.get("attached_node") or None
            ids = [attached] if attached else node.get("depends_on", {}).get("nodes", [])
            targets = [nodes[i] for i in ids if i in nodes and nodes[i]["resource_type"] == "model"]
            reason = f"teste {node['name']}: {result}"
        else:
            continue
        for target in targets:
            out.setdefault((target["schema"], target["name"]), reason)
    return out


def unchanged(
    con: warehouse.Connection, settings: Settings, published: dict[str, Any]
) -> set[tuple[str, str]]:
    """Tabelas que o dbt não refez desde o manifesto publicado: a impressão digital delas não muda (ADR 0047).

    Uma tabela só entra se o último resultado do modelo foi sucesso e a execução que o produziu começou
    ANTES do export que gerou o manifesto, e se o código é o mesmo (descrições e chaves entram na
    impressão). Sem manifesto do dbt ou do lake, ou com o código diferente, nenhuma: tudo é recalculado."""
    file = dbt.target_dir(settings) / "manifest.json"
    exported = published.get("dt_exportacao")
    same_code = published.get("versao_commit") == runs.code_version()
    if not (file.exists() and exported and same_code) or runs.code_version().endswith("+dirty"):
        return set()
    since = datetime.fromisoformat(exported).astimezone(UTC).replace(tzinfo=None)
    nodes = json.loads(file.read_text(encoding="utf-8"))["nodes"]
    found = con.execute(
        "SELECT t.id_no FROM metadata.testes_resultados t JOIN metadata.execucoes e USING (id_execucao) "
        "WHERE t.tipo = 'model' GROUP BY t.id_no HAVING arg_max(t.resultado, t.id_execucao) = 'success' "
        "AND arg_max(e.dt_inicio, t.id_execucao) < ?",
        (since,),
    ).fetchall()
    return {(n["schema"], n["name"]) for (i,) in found if (n := nodes.get(i)) and "schema" in n}


def _files(con: warehouse.Connection, root: str, pattern: str) -> list[dict[str, Any]]:
    """Arquivo, linhas, bytes e SHA-256 dos Parquet que casam com `pattern`, lidos de onde estão."""
    found = con.execute(
        f"SELECT filename, size, sha256(content) FROM read_blob('{lake.q(root)}/{pattern}') ORDER BY 1"
    ).fetchall()
    return [
        {
            "arquivo": name.replace("\\", "/")[len(root) + 1 :],
            "linhas": con.execute(f"SELECT count(*) FROM read_parquet('{lake.q(name)}')").fetchone()[0],  # type: ignore[index]
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
    kv = ", ".join(f"{k}: '{lake.q(v)}'" for k, v in meta.items())
    con.execute(
        f"COPY ({select}) TO '{lake.q(target)}' (FORMAT parquet, COMPRESSION zstd, COMPRESSION_LEVEL 3, "
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


def write_table(
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
    """Grava a tabela (arquivo único ou pasta por ano) em `<key>/<id_execucao>/` e devolve os arquivos.

    O caminho é próprio da execução (ADR 0052): o publicado nunca é sobrescrito; acrescenta `ano` às colunas.
    """
    folder = f"{key}/{meta['id_execucao']}"
    target = f"{root}/{folder}"
    if not root.startswith("r2://"):
        Path(target).mkdir(parents=True, exist_ok=True)
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
        full = select if has_year else select.replace(" FROM ", f", ({expr}) AS {YEAR_COLUMN} FROM ", 1)
        # Um COPY por ano, em ordem: o PARTITION_BY mantém um escritor aberto por ano e estoura a memória
        # em tabela grande; aqui cada COPY segura um arquivo só, no mesmo layout (`ano=AAAA/part-0.parquet`).
        for (year,) in con.execute(f"SELECT DISTINCT {YEAR_COLUMN} FROM ({full}) ORDER BY 1").fetchall():
            if not root.startswith("r2://"):
                Path(target, f"{YEAR_COLUMN}={year}").mkdir(parents=True, exist_ok=True)
            _copy(
                con,
                f"SELECT * FROM ({full}) WHERE {YEAR_COLUMN} = {int(year)}",
                f"{target}/{YEAR_COLUMN}={year}/part-0.parquet",
                meta,
            )
        return _files(con, root, f"{folder}/**/*.parquet")
    file = f"{folder}/{key.rsplit('/', 1)[1]}.parquet"
    _copy(con, f"{select} ORDER BY ({expr})" if expr else select, f"{root}/{file}", meta)
    return _files(con, root, file)


def fingerprint(
    con: warehouse.Connection, schema: str, table: str, key: str, expr: str | None
) -> dict[str, Any] | None:
    """Descrição, colunas, linhas e impressão digital da tabela (uma varredura); None sem coluna pública.

    Roda num cursor próprio (só leitura), então várias tabelas podem ser calculadas ao mesmo tempo.
    """
    start = time.monotonic()
    cur = warehouse.cursor(con)
    try:
        description, columns = _describe(cur, schema, table)
        if not columns:
            return None
        cols = ", ".join(f'"{c["nome"]}"' for c in columns)
        select = f'SELECT {cols} FROM {schema}."{table}"'
        rows, xor, total = cur.execute(  # xor sozinho zera pares de linhas iguais; a soma não
            f"SELECT count(*), coalesce(bit_xor(hash(t)), 0), coalesce(sum(hash(t)::HUGEINT), 0) "
            f"FROM ({select}) t"
        ).fetchone()  # type: ignore[misc]
    finally:
        cur.close()
    names = [(c["nome"], c["tipo"], c["descricao"]) for c in columns]
    digest = hashlib.sha256(f"{rows}:{xor}:{total}:{names}:{key}:{expr}:{description}".encode()).hexdigest()
    return {
        "description": description,
        "columns": columns,
        "select": select,
        "rows": rows,
        "fingerprint": digest,
        "seconds": time.monotonic() - start,
    }
