"""Catálogo de dados, gerado do `manifest.json` do dbt: não há lista paralela para manter.

Cada tabela é descrita onde nasce (fontes e modelos do dbt, com `description` e `meta`), e o catálogo
é a leitura disso. Um teste confere que as tabelas do warehouse e as do catálogo coincidem.
"""

import json
from typing import Any

from plataforma_dados.core.settings import Settings
from plataforma_dados.transformation import dbt

LAYERS = ("raw", "staging", "intermediate", "marts", "identity", "metadata")


def manifest(settings: Settings) -> dict[str, Any]:
    """Roda `dbt parse` e devolve o manifesto do projeto."""
    outcome = dbt.invoke(settings, "parse")
    file = dbt.target_dir(settings) / "manifest.json"
    if outcome.returncode != 0 or not file.exists():
        raise RuntimeError(f"dbt parse falhou: {outcome.output}")
    data: dict[str, Any] = json.loads(file.read_text(encoding="utf-8"))
    return data


def _rank(schema: str) -> int:
    """Posição da camada no fluxo; os schemas `raw_<esfera>_<fonte>` vêm primeiro."""
    layer = "raw" if schema.startswith("raw_") else schema
    return LAYERS.index(layer) if layer in LAYERS else len(LAYERS)


def tables(settings: Settings) -> list[dict[str, str]]:
    """Todas as tabelas declaradas (fontes e modelos), com esquema, descrição e metadados."""
    data = manifest(settings)
    found: list[dict[str, str]] = []
    for source in data["sources"].values():
        meta = {**source.get("source_meta", {}), **source.get("meta", {})}
        found.append(_entry(source["schema"], source["name"], source, meta))
    for node in data["nodes"].values():
        if node["resource_type"] == "model":
            found.append(_entry(node["schema"], node.get("alias") or node["name"], node, node["meta"]))
    return sorted(found, key=lambda t: (_rank(t["schema"]), t["schema"], t["name"]))


def columns(settings: Settings) -> list[dict[str, str]]:
    """Colunas dos marts (o contrato com a aplicação), com tipo e descrição."""
    found: list[dict[str, str]] = []
    for node in manifest(settings)["nodes"].values():
        if node["resource_type"] == "model" and node["schema"] == "marts":
            for column in node["columns"].values():
                found.append(
                    {
                        "table": node.get("alias") or node["name"],
                        "name": column["name"],
                        "type": str(column.get("data_type") or ""),
                        "description": " ".join(str(column.get("description") or "").split()),
                        "pii": "sim" if (column.get("meta") or {}).get("pii") else "",
                    }
                )
    return found


def _entry(schema: str, name: str, node: dict[str, Any], meta: dict[str, Any]) -> dict[str, str]:
    return {
        "schema": schema,
        "name": name,
        "description": " ".join(str(node.get("description") or "").split()),
        "sensitivity": str(meta.get("sensitivity", "")),
        "grain": str(meta.get("grain", "")),
    }


def markdown(settings: Settings) -> str:
    """O catálogo como documento (`docs/dados/catalogo.md`)."""
    lines = [
        "# Catálogo de dados",
        "",
        "Gerado do projeto dbt (`plataforma catalog`). Não edite à mão: edite a "
        "descrição e o `meta` do modelo ou da fonte e gere de novo.",
        "",
    ]
    all_tables = tables(settings)
    for schema in dict.fromkeys(t["schema"] for t in all_tables):
        chosen = [t for t in all_tables if t["schema"] == schema]
        lines += [
            f"## {schema}",
            "",
            "| Tabela | O que é | Sensibilidade | Grain |",
            "| --- | --- | --- | --- |",
        ]
        for t in chosen:
            lines.append(f"| `{t['name']}` | {t['description']} | {t['sensitivity']} | {t['grain']} |")
        lines.append("")
    lines += ["## Dicionário de colunas dos marts", ""]
    by_table: dict[str, list[dict[str, str]]] = {}
    for c in columns(settings):
        by_table.setdefault(c["table"], []).append(c)
    for table in sorted(by_table):
        lines += [
            f"### marts.{table}",
            "",
            "| Coluna | Tipo | Descrição | Dado pessoal |",
            "| --- | --- | --- | --- |",
        ]
        lines += [
            f"| `{c['name']}` | {c['type']} | {c['description']} | {c['pii']} |" for c in by_table[table]
        ]
        lines.append("")
    return "\n".join(lines)
