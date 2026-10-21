"""Qualidade dos dados: o resultado dos testes do dbt e do frescor, guardado em `metadata.dbt_results`.

Os testes em si são do dbt (genéricos, singulares e de contrato, em `transformation/`); aqui só se
registra o resultado de cada execução para a aplicação poder mostrá-lo.
"""

from typing import Any

from plataforma_dados.core import runs
from plataforma_dados.core.warehouse import Connection


def kind_of(unique_id: str) -> str:
    """test | freshness | model, a partir do `unique_id` do dbt."""
    prefix = unique_id.split(".", 1)[0]
    return {"test": "test", "source": "freshness"}.get(prefix, "model")


def record(con: Connection, run_id: int, results: list[dict[str, Any]]) -> None:
    """Grava o resultado de cada nó do dbt (modelo, teste ou frescor) de uma execução."""
    if not results:
        return
    moment = runs.now()
    con.executemany(
        "INSERT INTO metadata.dbt_results VALUES (?, ?, ?, ?, ?, ?, ?)",
        [
            (
                run_id,
                r["unique_id"],
                kind_of(str(r["unique_id"])),
                r["status"],
                r["failures"],
                r["message"],
                moment,
            )
            for r in results
        ],
    )
