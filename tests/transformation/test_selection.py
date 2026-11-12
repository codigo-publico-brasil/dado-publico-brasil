"""Seleção dos nós do dbt por mudança de dado (ADR 0047): quem entra, quem é pulado e quando tudo se refaz.

Manifesto e histórico montados à mão (rápido); a equivalência com a reconstrução completa, no pipeline
sintético, está em `tests/orchestration/test_selective_build.py`.
"""

import json
from datetime import date
from typing import Any

import pytest

from dado_publico_brasil.core import runs
from dado_publico_brasil.core.settings import Settings
from dado_publico_brasil.core.warehouse import Connection
from dado_publico_brasil.transformation import dbt, quality, selection

SUNDAY, MONDAY = date(2026, 11, 8), date(2026, 11, 9)
NIGHT_1, NIGHT_2 = "2026-11-06T04:00:00+00:00", "2026-11-09T04:00:00+00:00"


def _model(name: str, deps: list[str], pre: bool = False, periodo: str | None = None) -> dict[str, Any]:
    meta = {"periodo": periodo} if periodo else {}
    return {
        "unique_id": f"model.p.{name}",
        "resource_type": "model",
        "package_name": "p",
        "name": name,
        "schema": "marts",
        "tags": (["pre_identity"] if pre else []) + (["data_atual"] if periodo else []),
        "config": {"meta": meta},
        "depends_on": {"nodes": deps},
    }


MANIFEST: dict[str, Any] = {
    "metadata": {"project_name": "p"},
    "sources": {
        "source.p.camara.deputados": {
            "source_name": "camara",
            "name": "deputados",
            "schema": "raw_federal_camara",
        },
        "source.p.camara.deputados__filho": {
            "source_name": "camara",
            "name": "deputados__filho",
            "schema": "raw_federal_camara",
        },
        "source.p.tse.votacao": {"source_name": "tse", "name": "votacao", "schema": "raw_federal_tse"},
        "source.p.identity.pessoas": {"source_name": "identity", "name": "pessoas", "schema": "identity"},
        "source.p.metadata.capturas": {"source_name": "metadata", "name": "capturas", "schema": "metadata"},
    },
    "nodes": {
        n["unique_id"]: n
        for n in [
            _model("stg_camara", ["source.p.camara.deputados__filho"], pre=True),
            _model("stg_tse", ["source.p.tse.votacao"], pre=True),
            _model("stg_capturas", ["source.p.metadata.capturas"], pre=True),
            _model("int_camara", ["model.p.stg_camara"], pre=True),
            _model("stg_identity", ["source.p.identity.pessoas"]),
            _model("mart_camara", ["model.p.int_camara", "model.p.stg_identity"]),
            _model("mart_tse", ["model.p.stg_tse"]),
            _model("mart_mes", ["model.p.stg_tse"], periodo="mes"),
            _model("mart_ano", ["model.p.stg_tse"], periodo="ano"),
        ]
    }
    | {
        "test.p.t_mart_camara": {
            "unique_id": "test.p.t_mart_camara",
            "resource_type": "test",
            "package_name": "p",
            "name": "t_mart_camara",
            "attached_node": "model.p.mart_camara",
            "depends_on": {"nodes": ["model.p.mart_camara"]},
        }
    },
}
PRE = {"stg_camara", "stg_tse", "stg_capturas", "int_camara"}
POST = {"stg_identity", "mart_camara", "mart_tse", "mart_mes", "mart_ano"}


@pytest.fixture(autouse=True)
def _commit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(runs, "code_version", lambda: "v1")


@pytest.fixture
def env(con: Connection, settings: Settings) -> tuple[Connection, Settings]:
    target = dbt.target_dir(settings)
    target.mkdir(parents=True)
    (target / "manifest.json").write_text(json.dumps(MANIFEST), encoding="utf-8")
    return con, settings


def built(
    con: Connection,
    stage: str,
    started: str,
    names: set[str],
    status: dict[str, str] | None = None,
    models: set[str] | None = None,
) -> None:
    """Uma execução completa da fase em que cada modelo em `names` terminou como `status` (padrão: success).

    `models` (padrão: os próprios `names`) é o que a fase tinha de construir; maior que `names` = incompleta."""
    plan = selection.Plan(stage, True, "", frozenset(f"model.p.{n}" for n in (models or names)))
    results = [
        {"unique_id": f"model.p.{n}", "status": (status or {}).get(n, "success"), "failures": None,
         "message": None, "seconds": 1.0}
        for n in names
    ]  # fmt: skip
    quality.record_stage(con, stage, results, started, plan)


def loaded(con: Connection, fonte: str, dataset: str, when: str) -> None:
    con.execute(
        "INSERT INTO metadata.capturas (fonte, dataset, url, sha256, qtd_bytes, caminho, dt_captura, "
        "dt_verificacao, dt_carga) VALUES (?, ?, 'u', ?, 1, 'c', ?, ?, ?)",
        (fonte, dataset, when, when, when, when),
    )


def identity_run(con: Connection, when: str, before: str, after: str) -> None:
    with runs.track(con, "identity", started=when) as run:
        run.impressao_antes, run.impressao_depois = before, after
    con.execute("UPDATE metadata.execucoes SET dt_fim = ? WHERE etapa = 'identity'", (when,))


def settled(con: Connection) -> None:
    """Noite 1: as duas fases completas, no mesmo código."""
    built(con, "transform_pre", NIGHT_1, PRE)
    built(con, "transform_post", NIGHT_1, POST)


def pick(env: tuple[Connection, Settings], stage: str, today: date = MONDAY) -> selection.Plan:
    return selection.plan(env[0], env[1], stage, today)


def test_without_any_state_everything_is_rebuilt(env: tuple[Connection, Settings]) -> None:
    plan = pick(env, "transform_pre")
    assert plan.full and not plan.skip
    assert plan.args == ("--select", "tag:pre_identity", "--indirect-selection", "cautious")
    assert pick(env, "transform_post").args[:2] == ("--exclude", "tag:pre_identity")


def test_without_manifest_everything_is_rebuilt(con: Connection, settings: Settings) -> None:
    built(con, "transform_pre", NIGHT_1, PRE)
    assert selection.plan(con, settings, "transform_pre", MONDAY).full


def test_nothing_changed_skips_the_phase(env: tuple[Connection, Settings]) -> None:
    settled(env[0])
    loaded(env[0], "camara", "deputados", "2026-11-05T01:00:00+00:00")  # antes da construção
    for stage in ("transform_pre", "transform_post"):
        plan = pick(env, stage)
        assert not plan.full and plan.skip and plan.names == ()


@pytest.mark.parametrize("commit", ["v2", "v1+dirty", "unknown"])
def test_another_commit_or_uncommitted_code_rebuilds_everything(
    env: tuple[Connection, Settings], monkeypatch: pytest.MonkeyPatch, commit: str
) -> None:
    settled(env[0])
    monkeypatch.setattr(runs, "code_version", lambda: commit)
    assert pick(env, "transform_pre").full and pick(env, "transform_post").full


def test_the_weekly_rebuild_happens_on_sunday_once(env: tuple[Connection, Settings]) -> None:
    settled(env[0])
    assert not pick(env, "transform_pre", MONDAY).full
    assert pick(env, "transform_pre", SUNDAY).full  # a última completa é de 06/11
    built(env[0], "transform_pre", "2026-11-08T07:00:00+00:00", PRE)  # a de domingo
    assert not pick(env, "transform_pre", SUNDAY).full


def test_a_full_run_that_did_not_cover_every_model_does_not_count(env: tuple[Connection, Settings]) -> None:
    built(env[0], "transform_pre", NIGHT_1, {"stg_camara"}, models=PRE)
    assert pick(env, "transform_pre").full


def test_new_data_selects_its_readers_and_their_descendants_only_within_the_phase(
    env: tuple[Connection, Settings],
) -> None:
    settled(env[0])
    loaded(env[0], "camara", "deputados", "2026-11-07T01:00:00+00:00")  # a tabela filha conta pelo dataset
    pre, post = pick(env, "transform_pre"), pick(env, "transform_post")
    assert set(pre.names) == {"stg_camara", "int_camara"} and not pre.full
    assert set(post.names) == {"mart_camara"}
    assert {name for _, name in pre.skipped} == {"stg_tse", "stg_capturas"}


def test_the_skipped_come_parent_before_child_because_dagster_requires_it(
    env: tuple[Connection, Settings],
) -> None:
    settled(env[0])
    loaded(env[0], "tse", "votacao", "2026-11-07T01:00:00+00:00")
    order = [name for _, name in pick(env, "transform_pre").skipped]
    assert order.index("stg_camara") < order.index("int_camara")  # alfabética seria o contrário


def test_the_captures_table_is_not_a_trigger_and_a_source_without_loads_does_not_select(
    env: tuple[Connection, Settings],
) -> None:
    settled(env[0])
    loaded(env[0], "metadata", "capturas", "2026-11-07T01:00:00+00:00")
    assert pick(env, "transform_pre").skip


def test_a_failed_absent_or_skipped_node_is_selected_with_all_its_descendants(
    env: tuple[Connection, Settings],
) -> None:
    built(env[0], "transform_pre", NIGHT_1, PRE, {"stg_camara": "error"})
    built(env[0], "transform_post", NIGHT_1, POST - {"mart_tse"}, {"mart_mes": "skipped"})
    assert set(pick(env, "transform_pre").names) == {"stg_camara", "int_camara"}
    assert set(pick(env, "transform_post").names) == {
        "mart_tse",
        "mart_mes",
        "mart_camara",
    }  # o último, por int_camara


def test_a_failed_test_rebuilds_the_model_it_tests(env: tuple[Connection, Settings]) -> None:
    settled(env[0])
    with runs.track(env[0], "transform_post", "dbt", started=NIGHT_1) as run:
        quality.record(
            env[0],
            run.id,
            [
                {
                    "unique_id": "test.p.t_mart_camara",
                    "status": "fail",
                    "failures": 3,
                    "message": None,
                    "seconds": 1,
                }
            ],
        )
    assert set(pick(env, "transform_post").names) == {"mart_camara"}


def test_a_node_older_than_its_parent_is_selected_even_if_the_parent_ran_in_the_other_phase(
    env: tuple[Connection, Settings],
) -> None:
    """O pai foi refeito esta noite na fase 1; o filho, da fase 2, ainda é da noite anterior."""
    settled(env[0])
    built(env[0], "transform_pre", NIGHT_2, {"stg_camara", "int_camara"})
    assert set(pick(env, "transform_post").names) == {"mart_camara"}


def test_a_changed_identity_selects_its_readers_and_an_equal_one_selects_nothing(
    env: tuple[Connection, Settings],
) -> None:
    settled(env[0])
    identity_run(env[0], "2026-11-06T04:30:00+00:00", "a", "a")  # igual antes e depois
    assert pick(env, "transform_post").skip
    identity_run(env[0], "2026-11-07T04:30:00+00:00", "a", "b")  # uma ligação nova
    assert set(pick(env, "transform_post").names) == {"stg_identity", "mart_camara"}
    built(env[0], "transform_post", NIGHT_2, {"stg_identity", "mart_camara"})
    assert pick(env, "transform_post").skip  # já refeitos depois da mudança


def test_a_node_that_depends_on_the_period_enters_only_when_the_period_changes(
    env: tuple[Connection, Settings],
) -> None:
    settled(env[0])  # construído em 06/11
    assert pick(env, "transform_post", date(2026, 11, 30)).skip
    assert set(pick(env, "transform_post", date(2026, 12, 1)).names) == {"mart_mes"}
    assert set(pick(env, "transform_post", date(2027, 1, 1)).names) == {"mart_mes", "mart_ano"}


def test_the_selective_command_is_the_phase_minus_the_skipped_with_eager_tests(
    env: tuple[Connection, Settings],
) -> None:
    settled(env[0])
    loaded(env[0], "tse", "votacao", "2026-11-08T01:00:00+00:00")
    pre, post = pick(env, "transform_pre"), pick(env, "transform_post")
    assert set(pre.names) == {"stg_tse"}
    assert pre.args[:2] == ("--select", "tag:pre_identity") and pre.args[2] == "--exclude"
    assert set(pre.args[3].split()) == {"stg_camara", "stg_capturas", "int_camara"}
    assert pre.args[4:] == ("--indirect-selection", "eager")
    assert post.args[0] == "--exclude" and "tag:pre_identity" in post.args[1].split()


def test_the_first_build_counts_as_complete_with_the_manifest_the_dbt_wrote_during_it(
    con: Connection, settings: Settings
) -> None:
    plan = selection.plan(con, settings, "transform_pre", MONDAY)  # ainda sem manifesto
    assert plan.full and not plan.models
    target = dbt.target_dir(settings)
    target.mkdir(parents=True)
    (target / "manifest.json").write_text(json.dumps(MANIFEST), encoding="utf-8")
    results = [{"unique_id": f"model.p.{n}"} for n in PRE]
    assert plan.completed(results) and not plan.completed(results[:-1])


def test_a_seed_has_no_node_dependencies(env: tuple[Connection, Settings]) -> None:
    seed = {**_model("dim_seed", []), "resource_type": "seed", "depends_on": {"macros": []}}
    MANIFEST["nodes"]["model.p.dim_seed"] = seed
    try:
        file = dbt.target_dir(env[1]) / "manifest.json"
        file.write_text(json.dumps(MANIFEST), encoding="utf-8")
        settled(env[0])
        built(env[0], "transform_post", NIGHT_1, POST | {"dim_seed"})
        assert pick(env, "transform_post").skip
    finally:
        del MANIFEST["nodes"]["model.p.dim_seed"]


def test_a_change_to_the_identity_between_two_runs_also_counts(env: tuple[Connection, Settings]) -> None:
    settled(env[0])
    identity_run(env[0], "2026-11-06T04:30:00+00:00", "a", "a")
    assert pick(env, "transform_post").skip
    identity_run(env[0], "2026-11-07T04:30:00+00:00", "b", "b")  # mexeram nela fora da etapa
    assert set(pick(env, "transform_post").names) == {"stg_identity", "mart_camara"}


def test_phase_log_summarises_skipped_and_built_models_with_minutes() -> None:
    plan = selection.Plan("transform_post", False, "x", frozenset(), skipped=(("staging", "stg_a"),))
    results = [
        {"unique_id": "model.p.m_b", "status": "success", "seconds": 90.0},
        {"unique_id": "model.p.m_c", "status": "error", "seconds": 6.0},
        {"unique_id": "test.p.t", "status": "pass", "seconds": 1.0},
    ]
    lines = selection.phase_log(plan, results)
    assert lines[0] == "dbt transform_post: 1 pulados, 2 reconstruídos (1,6 min somados), 1 com erro"
    assert "  stg_a: pulado" in lines
    assert lines[2] == "  m_b: success (1,5 min)" and "  m_c: error (0,1 min)" in lines


def test_the_period_unit_day_changes_every_day() -> None:
    assert selection._period(date(2026, 11, 6), "dia") != selection._period(date(2026, 11, 7), "dia")
    assert selection._period(date(2026, 11, 6), "mes") == selection._period(date(2026, 11, 7), "mes")
