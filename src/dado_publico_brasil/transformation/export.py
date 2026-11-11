"""Exporta o lakehouse público em Parquet (ADR 0035): staging de fonte, intermediate, marts e as capturas.

Lê o warehouse só para leitura e grava na raiz do lake: o bucket do R2 (`r2://bucket`, pelo `httpfs`
do DuckDB, sem cópia local) se DADO_PUBLICO_R2_* estiver completo; senão `<storage_root>/lake/` (dev):

    staging/<poder>/<esfera>/<fonte>/<modelo>    (a árvore de `sources/`; a fonte sai de `stg_<fonte>__...`)
    intermediate/<modelo>
    marts/<dominio>/<tabela>                     (domínio = pasta do modelo no dbt)
    metadata/capturas

Cada tabela é `<caminho>.parquet` (um arquivo, ordenado pelo período se tiver `meta.particao`) ou, se tiver
`meta.particao` (expressão SQL do ano, declarada no dbt) e a estimativa passar de `max_bytes`,
`<caminho>/ano=AAAA/part-0.parquet`. Ano nulo é erro. Mais, na raiz:
    manifesto.json    arquivo, linhas, bytes, sha256, impressão, esquema, partição e descrições de cada tabela
    catalogo.duckdb   uma view por tabela (lista explícita de arquivos), com COMMENT de tabela e coluna

Idempotente e barato de repetir: cada tabela leva uma impressão digital do conteúdo, calculada no DuckDB numa
varredura (contagem, XOR dos hashes das linhas, que não depende da ordem, esquema e caminho), várias tabelas
ao mesmo tempo. Se for igual à do manifesto anterior (lido da raiz), a tabela é ignorada. Se nada mudou, nada
é gravado nem enviado (nem catálogo, nem manifesto). Senão, catálogo e manifesto são trocados por último; só
então se apagam os objetos órfãos sob os caminhos das tabelas gravadas (mudança de arquivo único para
partição); com `prune`, sob todos (tabela removida). Nunca exporta `raw`, `identity` nem colunas de
documento pessoal. Imprime o progresso: uma linha por tabela e o tempo de cada fase.

Arquivos (ADR 0037): dataset com `arquivos.publicar: true` no YAML da fonte vira uma coleção `arq_<nome>`
ao lado das tabelas da fonte (`staging/<poder>/<esfera>/<fonte>/arq_<nome>/...`), lida de
`<pasta de dados>/arquivos/` (a carga materializa), com a tabela de controle `arq_<nome>.parquet` (um arquivo
por linha, com hash). Só sobe o que falta ou mudou; o que saiu da fonte só é apagado com `prune`.

Dividido por responsabilidade: `tables` (tabelas), `colecoes` (arquivos), `lake` (raiz, manifesto, catálogo),
`verify` (conferência) e `core/s3.py` (requisições assinadas). Este módulo só orquestra.
"""

import hashlib
import json
import os
import re
import shutil
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from typing import Any

from dado_publico_brasil.core import runs
from dado_publico_brasil.core.settings import Settings
from dado_publico_brasil.transformation import colecoes, lake, tables


def export(
    settings: Settings, base_url: str | None = None, max_bytes: int = tables.MAX_BYTES, prune: bool = False
) -> dict[str, int]:
    """Exporta o lake para a raiz (R2 ou pasta local).

    Devolve tabelas, gravadas, ignoradas, excluídas (teste ou modelo em erro: ficam na versão anterior),
    órfãos e bytes.

    Recusa, sem apagar nem publicar nada, se faltar no warehouse uma tabela do manifesto anterior (warehouse
    errado ou incompleto); `prune=True` autoriza a retirada dela do lake.
    """
    base = base_url or os.environ.get(lake.ENV_URL) or ""
    root = lake.location(settings)
    if lake.r2() and not base:
        raise ValueError(
            f"defina {lake.ENV_URL} (URL pública do lake) para exportar ao R2 (veja .env.example)"
        )
    now = datetime.now(UTC)
    meta = {
        "id_execucao": now.strftime("%Y%m%dT%H%M%SZ"),
        "dt_exportacao": now.isoformat(timespec="seconds"),
        "versao_commit": runs.code_version(),
    }
    models = tables.models(settings)
    entries: list[dict[str, Any]] = []
    tempos: dict[str, dict[str, Any]] = {}  # tempo por tabela, guardado em `state_dir/export_tempos.json`
    written = ignored = excluded = size = 0
    con = lake.connect(settings, warehouse_file=True)
    try:
        published = lake.read_manifest(con, root)
        old_entries = published.get("tabelas", [])
        before = {(e["camada"], e["tabela"]): e for e in old_entries if not e["tabela"].startswith("arq_")}
        old_files = {e["caminho"]: e for e in old_entries if e["tabela"].startswith("arq_")}
        touched = {e.get("caminho", f"{e['camada']}/{e['tabela']}") for e in old_entries}
        relations = tables.relations(con)
        keep: set[str] = set()
        missing = sorted(f"{c}.{t}" for c, t in before if (c, t) not in set(relations))
        if missing and not prune:
            raise ValueError(
                f"o warehouse não tem {len(missing)} tabela(s) do manifesto publicado "
                f"({', '.join(missing[:5])}{'...' if len(missing) > 5 else ''}); "
                "nada foi apagado nem publicado. "
                "Confira o warehouse ou use --prune para retirá-las do lake"
            )
        collections = colecoes.collect(con, settings, prune)
        gone = sorted(k for k in old_files if not collections.get(k))
        if gone and not prune:
            raise ValueError(
                f"a coleção {', '.join(gone)} está no manifesto publicado mas saiu do YAML da fonte ou não "
                "tem arquivo no disco; nada foi apagado nem publicado. Confira `arquivos/` e o contrato "
                "ou use --prune"
            )
        keys = {
            r: tables.table_path(models, *r) for r in relations
        }  # falha cedo, antes de gravar qualquer arquivo
        exprs = {r: models.get(r[1], {}).get("config", {}).get("meta", {}).get("particao") for r in relations}
        held = tables.blocked(con, settings)  # teste ou modelo em erro: fica a versão anterior, com o motivo
        reuse = {  # o dbt não refez: a entrada do manifesto anterior vale, sem ler a tabela (ADR 0047)
            r
            for r in tables.unchanged(con, settings, published)
            if r in before and "excluida_por" not in before[r] and r not in held
        }
        with lake.phase("impressões digitais"), ThreadPoolExecutor(tables.FINGERPRINTS) as pool:
            prints = list(
                pool.map(
                    lambda r: (
                        None
                        if r in held or r in reuse
                        else tables.fingerprint(con, r[0], r[1], keys[r], exprs[r])
                    ),
                    relations,
                )
            )
        state = {"entries": old_entries, "base": published.get("base")}

        def commit(current: list[dict[str, Any]]) -> None:
            """Troca catálogo e manifesto (por último, depois dos arquivos) se diferirem do publicado."""
            current = [{**e, "licenca": tables.licenca(e["caminho"])} for e in current]
            if json.loads(json.dumps(current)) == state["entries"] and state["base"] == (base or root):
                return  # nada mudou: o publicado já é este
            catalog = settings.state_dir / "catalogo.duckdb"
            lake.write_catalog(current, catalog, base or root, meta)
            if lake.r2():
                lake.request("PUT", "catalogo.duckdb", catalog)
            else:
                shutil.copyfile(catalog, f"{root}/catalogo.duckdb")
            catalog.unlink()
            text = json.dumps({**meta, "base": base or root, "tabelas": current}, ensure_ascii=True)
            con.execute(  # compacto: uma linha, sem aspas soltas
                f"COPY (SELECT ?) TO '{lake.q(root)}/manifesto.json' "
                "(FORMAT csv, HEADER false, QUOTE '', ESCAPE '', DELIMITER '\x01')",
                (text,),
            )
            state.update(entries=json.loads(json.dumps(current)), base=base or root)
            lake.say("  catálogo e manifesto trocados")

        written_keys: set[str] = set()  # caminhos de tabela a varrer atrás de órfãos
        changed: set[str] = set()  # tudo o que foi gravado, para as linhas de progresso
        with lake.phase("escrita"):
            for rel, found in zip(relations, prints, strict=True):
                if rel in held:
                    lake.say(f"  {rel[0]}.{rel[1]}: mantida a versão anterior ({held[rel]})")
                    excluded += 1
                    if rel in before:  # nunca publicada: nada a manter
                        entries.append({**before[rel], "excluida_por": held[rel]})
                    continue
                if rel in reuse:
                    entries.append(before[rel])
                    ignored += 1
                    tempos[f"{rel[0]}.{rel[1]}"] = {
                        "impressao_s": 0.0,
                        "escrita_s": 0.0,
                        "resultado": "reaproveitada",
                    }
                    lake.say(f"  {rel[0]}.{rel[1]}: reaproveitada (o dbt não a refez desde o último export)")
                    continue
                if not found:
                    continue
                (schema, table), key, expr = rel, keys[rel], exprs[rel]
                description, columns, rows = found["description"], found["columns"], found["rows"]
                fingerprint, old, start = found["fingerprint"], before.get(rel), time.monotonic()
                if old and old["impressao"] == fingerprint:
                    files, columns = old["arquivos"], old["colunas"]
                    ignored += 1
                else:
                    files = tables.write_table(
                        con,
                        settings,
                        root,
                        meta,
                        key,
                        found["select"],
                        expr,
                        description,
                        columns,
                        rows,
                        max_bytes,
                    )
                    written_keys.add(key)
                    if old and old.get("caminho", key) != key:
                        written_keys.add(old["caminho"])  # tabela mudou de caminho: o antigo fica órfão
                    changed.add(key)
                    written += 1
                    size += sum(f["bytes"] for f in files)
                result, spent = ("ignorada" if key not in changed else "gravada"), time.monotonic() - start
                tempos[f"{schema}.{table}"] = {
                    "impressao_s": round(found["seconds"], 1),
                    "escrita_s": round(spent, 1),
                    "resultado": result,
                }
                lake.say(
                    f"  {schema}.{table}: {result} (impressão {found['seconds']:.1f}s, escrita {spent:.1f}s)"
                )
                years = sorted({int(m[1]) for f in files if (m := re.search(r"/ano=(\d+)/", f["arquivo"]))})
                entries.append(
                    {
                        "camada": schema,
                        "camada_medalhao": tables.MEDALLION[schema],
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
        table_entries = list(entries)
        coll_entries = {e["caminho"]: e for e in old_entries if e["tabela"].startswith("arq_")}
        with lake.phase("catálogo e manifesto (tabelas)"):
            commit(table_entries + list(coll_entries.values()))  # queda nos arquivos não perde as tabelas
        con.close()  # a fase de arquivos não lê o warehouse: instância nova, sem a memória das tabelas
        con = lake.connect(settings, warehouse_file=False)
        with lake.phase("arquivos"):
            for key, files in collections.items():
                if not files and key not in old_files:
                    continue  # coleção que nunca teve arquivo não vira tabela vazia
                start, sent, resumed = time.monotonic(), 0, 0
                clean = [{k: v for k, v in f.items() if k != "local"} for f in files]
                fingerprint = hashlib.sha256(f"{key}:{clean}".encode()).hexdigest()
                old = old_files.get(key)
                description = colecoes.CONTROL_DESCRIPTION % key.rsplit("/", 1)[1]
                if old and old["impressao"] == fingerprint:  # mesmo controle: tudo já foi enviado
                    parquet, columns = old["arquivos"], old["colunas"]
                    ignored += 1
                else:
                    known: dict[str, str] = {}
                    if old:
                        known = dict(
                            con.execute(
                                f"SELECT caminho, sha256_arquivo FROM read_parquet('{lake.q(root)}/{key}.parquet')"  # noqa: E501
                            ).fetchall()
                        )
                    sent, resumed = colecoes.send(root, key, files, known)
                    size += sum(
                        f["qtd_bytes"] for f in files if known.get(f["caminho"]) != f["sha256_arquivo"]
                    )
                    parquet, description = colecoes.control(con, settings, root, meta, key, files)
                    columns = [{"nome": n, "tipo": t, "descricao": d} for n, t, d in colecoes.CONTROL_COLUMNS]
                    changed.add(key)  # coleção: objeto fora do controle só sai com --prune
                    written += 1
                lake.say(
                    f"  {key}: {'gravada' if key in changed else 'ignorada'} "
                    f"({len(files)} arquivos, {sent} enviados, {resumed} já no destino, "
                    f"{time.monotonic() - start:.1f}s)"
                )
                entries.append(
                    {
                        "camada": "staging",
                        "camada_medalhao": tables.MEDALLION["staging"],
                        "tabela": key.rsplit("/", 1)[1],
                        "caminho": key,
                        "descricao": description,
                        "linhas": len(files),
                        "impressao": fingerprint,
                        "particao": None,
                        "ano": None,
                        "colunas": columns,
                        "arquivos": parquet,
                    }
                )
                keep |= {f"{key}/{f['caminho']}" for f in files}
                coll_entries[key] = entries[-1]
                if key in changed:
                    commit(table_entries + list(coll_entries.values()))  # coleção concluída: registrada
        entries = table_entries + [coll_entries[k] for k in collections if k in coll_entries]
        with lake.phase("catálogo e manifesto"):
            commit(entries)
        keep |= {f["arquivo"] for e in entries for f in e["arquivos"]}
        # órfãos só sob o que foi gravado; `prune` varre tudo (tabela removida, arquivo que saiu da fonte)
        swept = written_keys | (touched | set(collections) if prune else set())
        with lake.phase("órfãos"):
            orphans = (
                lake.delete_orphans(con, root, swept, keep) if swept else 0
            )  # só depois do manifesto novo
        (settings.state_dir / "export_tempos.json").write_text(json.dumps(tempos, indent=1), encoding="utf-8")
    finally:
        con.close()
    return {
        "tabelas": len(entries),
        "gravadas": written,
        "ignoradas": ignored,
        "excluidas": excluded,
        "orfaos": orphans,
        "bytes": size,
    }
