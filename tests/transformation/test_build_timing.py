"""Tempo do dbt: `metadata.execucoes` mede o `dbt build` inteiro e `metadata.testes_resultados` guarda o tempo de cada nó."""

import json
import time
from pathlib import Path
from typing import Any

import pytest

from dado_publico_brasil.core import migrations
from dado_publico_brasil.core.settings import Settings
from dado_publico_brasil.core.warehouse import scalar
from dado_publico_brasil.transformation import build, dbt

NOS: list[dict[str, Any]] = [
    {"unique_id": "model.x.a", "status": "success", "failures": None, "message": "OK", "seconds": 12.5},
    {"unique_id": "test.x.t", "status": "pass", "failures": 0, "message": None, "seconds": 0.25},
    {"unique_id": "source.x.s", "status": "pass", "failures": None, "message": None, "seconds": None},
]


def test_read_results_brings_the_execution_time_of_each_node(tmp_path: Path) -> None:
    settings = Settings(storage_root=tmp_path)
    target = dbt.target_dir(settings)
    target.mkdir(parents=True)
    results = [{"unique_id": "model.x.a", "status": "success", "execution_time": 3.5}, {"unique_id": "t"}]
    (target / "run_results.json").write_text(json.dumps({"results": results}), encoding="utf-8")
    assert [r["seconds"] for r in dbt.read_results(settings)] == [3.5, None]


def test_the_run_covers_the_whole_dbt_build_and_each_node_keeps_its_time(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    settings = Settings(storage_root=tmp_path)

    def invoke(*args: Any, **kwargs: Any) -> dbt.Outcome:
        time.sleep(1.2)  # o `dbt build`; `execucoes` tem resolução de segundos
        return dbt.Outcome(0, "", NOS)

    monkeypatch.setattr(dbt, "invoke", invoke)
    build.transform(settings, "transform_pre")
    con = migrations.open_warehouse(settings)
    try:
        seconds = scalar(
            con,
            "SELECT date_diff('second', dt_inicio::TIMESTAMP, dt_fim::TIMESTAMP) FROM metadata.execucoes "
            "WHERE etapa = 'transform_pre'",
        )
        saved = dict(con.execute("SELECT id_no, qtd_segundos FROM metadata.testes_resultados").fetchall())
    finally:
        con.close()
    assert seconds >= 1
    assert saved == {"model.x.a": 12.5, "test.x.t": 0.25, "source.x.s": None}
