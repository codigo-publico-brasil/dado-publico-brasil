"""Bucket privado do R2 (ADR 0036): fonte da verdade da identidade e do metadata, que o landing não refaz.

Sem `DADO_PUBLICO_R2_BUCKET_PRIVADO` tudo fica local (desenvolvimento). Só a produção tem a variável
e o token com escrita: é isso que garante um único escritor. Os testes trocam `root` por uma pasta temporária.
"""

import os
from pathlib import Path

import duckdb

from dado_publico_brasil.core import rebuild
from dado_publico_brasil.core.settings import Settings
from dado_publico_brasil.core.warehouse import Connection, scalar

ENV = "DADO_PUBLICO_R2_BUCKET_PRIVADO"
KEYS = ("ACCOUNT_ID", "ACCESS_KEY_ID", "SECRET_ACCESS_KEY")
MARKER = "_concluido"


def credentials() -> dict[str, str]:
    """As três credenciais do token S3 do R2 (as mesmas do lake público); vazio se faltar alguma."""
    cfg = {k: os.environ.get(f"DADO_PUBLICO_R2_{k}", "") for k in KEYS}
    return cfg if all(cfg.values()) else {}


def secret(con: Connection) -> None:
    """Cria o segredo `lake` do R2 na conexão, se houver credenciais."""
    if cfg := credentials():
        quoted = {k: v.replace("'", "''") for k, v in cfg.items()}
        con.execute(
            f"CREATE OR REPLACE SECRET lake (TYPE r2, KEY_ID '{quoted['ACCESS_KEY_ID']}', "
            f"SECRET '{quoted['SECRET_ACCESS_KEY']}', ACCOUNT_ID '{quoted['ACCOUNT_ID']}')"
        )


def root(settings: Settings) -> str | None:
    """`r2://<bucket privado>[/prefixo]`, ou None no modo local."""
    bucket = os.environ.get(ENV, "").strip().strip("/")
    return f"r2://{bucket}" if bucket else None


def prepare(path: str) -> str:
    """Pasta local precisa existir antes do COPY; no R2 não há pastas."""
    if "://" not in path:
        Path(path).mkdir(parents=True, exist_ok=True)
    return path


def files(con: Connection, pattern: str) -> list[str]:
    """Arquivos que casam com `pattern` (o `glob` do DuckDB serve para a pasta local e para o R2)."""
    try:
        return sorted(
            r[0].replace("\\", "/") for r in con.execute("SELECT file FROM glob(?)", (pattern,)).fetchall()
        )
    except duckdb.IOException:
        return []


def snapshots(settings: Settings) -> str:
    """Pasta das cópias da identidade: no bucket privado, ou local sem ele."""
    return f"{root(settings) or settings.storage_root.as_posix()}/snapshots/identity"


def latest(con: Connection, settings: Settings) -> str | None:
    """A cópia mais recente da identidade que tem o marcador `_concluido` (pasta sem marcador é ignorada)."""
    done = files(con, f"{snapshots(settings)}/*/{MARKER}")
    return done[-1].rsplit("/", 1)[0] if done else None


def push_metadata(con: Connection, settings: Settings) -> None:
    """Regrava inteiro `metadata/<tabela>.parquet` no bucket privado. Recusa se o remoto tem mais capturas."""
    if (base := root(settings)) is None:
        return
    secret(con)
    remote = prepare(f"{base}/metadata")
    if files(con, f"{remote}/capturas.parquet*"):  # o glob sem curinga não confere a existência no R2
        there = scalar(con, f"SELECT count(*) FROM read_parquet('{remote}/capturas.parquet')")
        here = scalar(con, "SELECT count(*) FROM metadata.capturas")
        if there > here:
            raise RuntimeError(
                f"o bucket privado tem {there} capturas e esta máquina {here}: restaure antes de enviar"
            )
    for table in rebuild.TABLES:
        con.execute(f"COPY metadata.{table} TO '{remote}/{table}.parquet' (FORMAT parquet, COMPRESSION zstd)")


def restore(con: Connection, settings: Settings) -> None:
    """Traz o metadata e a identidade mais recente do bucket privado para um warehouse recém-migrado."""
    if (base := root(settings)) is None:
        return
    secret(con)
    for table in rebuild.TABLES:
        file = f"{base}/metadata/{table}.parquet"
        if files(con, f"{file}*"):
            con.execute(f"INSERT INTO metadata.{table} BY NAME SELECT * FROM read_parquet('{file}')")
    con.execute("UPDATE metadata.capturas SET dt_carga = NULL")  # o raw se refaz do landing
    if folder := latest(con, settings):
        for file in files(con, f"{folder}/*.parquet"):
            table = file.rsplit("/", 1)[1].removesuffix(".parquet")
            con.execute(f"INSERT INTO identity.{table} BY NAME SELECT * FROM read_parquet('{file}')")
    rebuild.advance_sequences(con)
