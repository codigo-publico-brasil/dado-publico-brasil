"""Descrições das tabelas e colunas do raw (ADR 0022).

O raw espelha a fonte nos nomes, mas também é descrito. A tabela leva a descrição declarada nas fontes do dbt
(`_<fonte>__sources.yml`); o que não foi declarado ganha um texto que diz apenas o que se sabe: o campo vem da
fonte, como publicado, sem tratamento. O significado de cada campo está na descrição da coluna do staging.
"""

import json
from pathlib import Path

from dado_publico_brasil.core.warehouse import Connection

INTERNAL = {
    "_source_file_id": (
        "Identificador da captura (metadata.captures.id): liga a linha ao arquivo original do landing, "
        "com hash e data."
    ),
    "_ingested_at": "Instante (UTC) em que a linha chegou ao raw, o da carga do arquivo de origem.",
    "_row_hash": "Impressão digital do conteúdo da linha, chave dos arquivos sem identificador natural.",
    "_item": "Item (identificador) que originou a linha, nos datasets buscados item a item.",
    "_dlt_id": "Identificador interno da linha, criado pelo dlt.",
    "_dlt_load_id": "Identificador interno da carga do dlt que gravou a linha.",
    "_dlt_parent_id": "Identificador interno da linha-pai, nas tabelas filhas criadas pelo dlt.",
    "_dlt_list_idx": "Posição da linha na lista aninhada de origem, nas tabelas filhas criadas pelo dlt.",
    "_dlt_root_id": "Identificador interno da linha raiz, nas tabelas filhas criadas pelo dlt.",
}


def _text(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def raw(con: Connection, manifest_dir: Path) -> int:
    """Grava `COMMENT ON` em cada tabela e coluna do raw. Devolve quantas tabelas foram descritas."""
    manifest = json.loads((manifest_dir / "manifest.json").read_text(encoding="utf-8"))
    declared = {(s["schema"], s["name"]): s for s in manifest["sources"].values()}
    tables = con.execute(
        "SELECT schema_name, table_name FROM duckdb_tables() "
        "WHERE starts_with(schema_name, 'raw_') AND NOT starts_with(table_name, '_dlt_') ORDER BY 1, 2"
    ).fetchall()
    for schema, table in tables:
        source = declared.get((schema, table), {})
        parent = table.split("__")[0]
        generic = (
            f"Tabela filha de `{parent}`, criada pelo dlt para os campos aninhados da fonte (`{table}`)."
            if "__" in table
            else f"Tabela `{table}` da fonte, como publicada, sem tratamento."
        )
        description = (source.get("description") or "").strip() or generic
        con.execute(f'COMMENT ON TABLE "{schema}"."{table}" IS {_text(description)}')
        columns = source.get("columns") or {}
        for (column,) in con.execute(
            "SELECT column_name FROM duckdb_columns() WHERE schema_name = ? AND table_name = ?",
            (schema, table),
        ).fetchall():
            described = (columns.get(column, {}).get("description") or "").strip()
            text = (
                described
                or INTERNAL.get(column)
                or f"Campo `{column}` da fonte, como publicado, sem tratamento."
            )
            con.execute(f'COMMENT ON COLUMN "{schema}"."{table}"."{column}" IS {_text(text)}')
    return len(tables)
