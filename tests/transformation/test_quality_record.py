"""Fase do dbt com nó em erro: todos os nós e tempos são gravados e a execução fica como erro, com duração."""

from typing import Any

from dado_publico_brasil.core import runs
from dado_publico_brasil.core.warehouse import Connection, scalar
from dado_publico_brasil.transformation import quality


def test_every_node_and_its_time_is_recorded_and_the_run_is_an_error_with_its_real_duration(
    con: Connection,
) -> None:
    results: list[dict[str, Any]] = [
        {"unique_id": "model.x.a", "status": "success", "failures": None, "message": None, "seconds": 1.5},
        {"unique_id": "model.x.b", "status": "error", "failures": None, "message": "boom", "seconds": 0.2},
        {"unique_id": "model.x.c", "status": "skipped", "failures": None, "message": None, "seconds": 0.0},
        {"unique_id": "test.x.t1", "status": "warn", "failures": 3, "message": None, "seconds": 0.7},
        {"unique_id": "test.x.t2", "status": "fail", "failures": 1, "message": None, "seconds": 0.4},
    ]
    bad = quality.record_stage(con, "transform_post", results, "2020-01-01T00:00:00+00:00")
    assert [r["unique_id"] for r in bad] == ["model.x.b", "test.x.t2"]
    assert scalar(con, "SELECT count(*) FROM metadata.testes_resultados") == 5
    assert scalar(con, "SELECT count(*) FROM metadata.testes_resultados WHERE qtd_segundos IS NULL") == 0
    assert scalar(con, "SELECT resultado FROM metadata.execucoes WHERE etapa = 'transform_post'") == "error"
    assert (
        scalar(con, "SELECT dt_inicio FROM metadata.execucoes").year == 2020
    )  # início real, não o da gravação
    assert scalar(con, "SELECT dt_fim IS NOT NULL FROM metadata.execucoes")
    quality.record_stage(con, "transform_pre", results[:1], runs.now())
    assert scalar(con, "SELECT resultado FROM metadata.execucoes WHERE etapa = 'transform_pre'") == "ok"
