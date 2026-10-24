"""Registro de execuções (`metadata.runs`): quando, com qual código, quantas linhas, com que resultado.

É a base do frescor, da auditoria e do agendamento.
"""

import subprocess
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import cache

from dado_publico_brasil.core.warehouse import Connection


def now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


@cache
def code_version() -> str:
    """Commit atual (com sufixo se houver alteração não commitada), para a linhagem."""

    def git(*args: str) -> str:
        r = subprocess.run(["git", *args], capture_output=True, text=True, timeout=10, check=False)
        return r.stdout.strip()

    try:
        commit = git("rev-parse", "--short", "HEAD")
        if not commit:
            return "unknown"
        return commit + ("+dirty" if git("status", "--porcelain") else "")
    except (OSError, subprocess.SubprocessError):
        return "unknown"


@dataclass
class Run:
    id: int
    rows_in: int = 0
    rows_out: int = 0


@contextmanager
def track(
    con: Connection,
    stage: str,
    source: str | None = None,
    dataset: str | None = None,
    year: int | None = None,
) -> Iterator[Run]:
    """Abre uma execução. Ao sair, marca `ok` ou `error` (e repassa a exceção)."""
    row = con.execute(
        "INSERT INTO metadata.runs (stage, source, dataset, year, started_at, code_version, status) "
        "VALUES (?, ?, ?, ?, ?, ?, 'running') RETURNING id",
        (stage, source, dataset, year, now(), code_version()),
    ).fetchone()
    assert row is not None
    run = Run(id=int(row[0]))
    try:
        yield run
    except BaseException as error:
        _close(con, run, "error", str(error))
        raise
    _close(con, run, "ok", None)


def _close(con: Connection, run: Run, status: str, message: str | None) -> None:
    con.execute(
        "UPDATE metadata.runs SET finished_at = ?, rows_in = ?, rows_out = ?, status = ?, "
        "message = ? WHERE id = ?",
        (now(), run.rows_in, run.rows_out, status, message, run.id),
    )
