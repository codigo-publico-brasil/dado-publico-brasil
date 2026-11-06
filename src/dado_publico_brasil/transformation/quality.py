"""Qualidade dos dados: o resultado dos testes do dbt e do frescor, guardado em `metadata.testes_resultados`.

Os testes em si são do dbt (genéricos, singulares e de contrato, em `transformation/`); aqui só se
registra o resultado de cada execução para a aplicação poder mostrá-lo.
"""

from typing import Any

from dado_publico_brasil.core import runs
from dado_publico_brasil.core.warehouse import Connection


def kind_of(unique_id: str) -> str:
    """test | freshness | model, a partir do `unique_id` do dbt."""
    prefix = unique_id.split(".", 1)[0]
    return {"test": "test", "source": "freshness"}.get(prefix, "model")


def record_stage(
    con: Connection, stage: str, results: list[dict[str, Any]], started: str, plan: Any = None
) -> list[dict[str, Any]]:
    """Grava a execução de uma fase do dbt e o resultado e o tempo de TODOS os nós (inclusive erro, aviso e
    pulados). A execução fica com resultado `error` e a duração real (`started`) se algum nó falhou, sem
    lançar exceção. Com o `plan` (de `selection.plan`), marca se a execução foi uma reconstrução completa
    de toda a fase. Devolve os nós reprovados (sem os pulados, que só seguem um erro a montante)."""
    with runs.track(con, stage, "dbt", started=started) as run:
        record(con, run.id, results)
        run.completa = bool(plan and plan.completed(results))
        bad = [r for r in results if r["status"] in ("error", "fail", "runtime error")]
        run.rows_in, run.rows_out = len(results), len(bad)
        if bad:
            run.result = "error"
            run.message = "; ".join(f"{r['unique_id']}: {r['status']}" for r in bad)[:2000]
    return bad


def record(con: Connection, run_id: int, results: list[dict[str, Any]]) -> None:
    """Grava o resultado de cada nó do dbt (modelo, teste ou frescor) de uma execução."""
    if not results:
        return
    moment = runs.now()
    con.executemany(
        "INSERT INTO metadata.testes_resultados "
        "(id_execucao, id_no, tipo, resultado, qtd_falhas, mensagem, dt_registro, qtd_segundos) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        [
            (
                run_id,
                r["unique_id"],
                kind_of(str(r["unique_id"])),
                r["status"],
                r["failures"],
                r["message"],
                moment,
                r.get("seconds"),
            )
            for r in results
        ],
    )
