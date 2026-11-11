"""Verificação do lake publicado: cada arquivo do manifesto existe, com os mesmos bytes e SHA-256."""

import os
from typing import Any

import duckdb

from dado_publico_brasil.core import warehouse
from dado_publico_brasil.core.settings import Settings
from dado_publico_brasil.transformation import lake


def _verify_collection(con: warehouse.Connection, base: str, table: dict[str, Any]) -> list[str]:
    """Coleção `arq_`: todo arquivo do controle existe com o mesmo hash e nada da pasta fica fora dele."""
    key = table["caminho"]
    control = table["arquivos"][0]["arquivo"]
    listed = con.execute(
        f"SELECT caminho, sha256_arquivo FROM read_parquet('{lake.q(base)}/{control}')"
    ).fetchall()
    found = []
    for name, sha in listed:
        try:
            row = con.execute(
                f"SELECT sha256(content) FROM read_blob('{lake.q(base)}/{key}/{lake.q(name)}')"
            ).fetchone()
        except duckdb.Error:
            row = None
        if not row:
            found.append(f"falta {key}/{name}")
        elif row[0] != sha:
            found.append(f"{key}/{name} difere do controle")
    try:  # bucket público não lista: objetos soltos só se conferem com pasta local ou segredo do R2
        stray = {f[len(base) + 1 :] for f in lake.glob(con, f"{base}/{key}/**")} - {
            f"{key}/{n}" for n, _ in listed
        }
    except duckdb.Error:
        stray = set()
    return found + [f"{name} fora do controle" for name in sorted(stray)]


def verify(settings: Settings, base_url: str | None = None) -> list[str]:
    """Lê o manifesto publicado e confere cada arquivo (existência, bytes e SHA-256). Devolve os problemas."""
    base = (base_url or os.environ.get(lake.ENV_URL) or lake.location(settings)).rstrip("/")
    con = lake.connect(settings, warehouse_file=False)
    try:
        manifest = lake.read_manifest(con, base)
        if not manifest:
            return [f"sem manifesto em {base}"]
        found = []
        for f in (f for t in manifest["tabelas"] for f in t["arquivos"]):
            try:
                row = con.execute(
                    f"SELECT size, sha256(content) FROM read_blob('{lake.q(base)}/{f['arquivo']}')"
                ).fetchone()
            except duckdb.Error:
                row = None
            if not row:
                found.append(f"falta {f['arquivo']}")
            elif row != (f["bytes"], f["sha256"]):
                found.append(f"{f['arquivo']} difere do manifesto")
        for t in (t for t in manifest["tabelas"] if t["tabela"].startswith("arq_")):
            found += _verify_collection(con, base, t)
        return found
    finally:
        con.close()
