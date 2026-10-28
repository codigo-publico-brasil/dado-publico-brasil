"""Saúde dos dados por dimensão de qualidade: classificação, notas e cobertura (issue 47)."""

from typing import Any

from dado_publico_brasil.core import runs
from dado_publico_brasil.core.settings import DBT_DIR, Settings
from dado_publico_brasil.core.warehouse import Connection
from dado_publico_brasil.transformation import health, observability, quality


def build_run(con: Connection, statuses: dict[str, str]) -> None:
    results: list[dict[str, Any]] = [
        {"unique_id": uid, "status": status, "failures": 1, "message": ""} for uid, status in statuses.items()
    ]
    with runs.track(con, "transform_post", "dbt") as run:
        quality.record(con, run.id, results)


def test_the_dimension_comes_from_the_test_name_or_the_folder() -> None:
    singular = {
        "candidaturas_sem_votos_carregados": "completeness",
        "pessoas_perdidas_aos_marts": "consistency",
    }
    expected = {
        "test.p.not_null_pessoas_id_pessoa.abc": "completeness",
        "test.p.unique_pessoas_id_pessoa.abc": "uniqueness",
        "test.p.dbt_utils_unique_combination_of_columns_resultados_x__y.abc": "uniqueness",
        "test.p.relationships_votos_id_pessoa__id_pessoa__ref_pessoas_.abc": "consistency",
        "test.p.accepted_values_votos_voto__sim__nao.abc": "validity",
        "test.p.elementary_freshness_anomalies_votos_.abc": "freshness",
        "test.p.elementary_volume_anomalies_votos_.abc": "completeness",
        "test.p.elementary_schema_changes_votos_.abc": "consistency",
        "test.p.source_not_null_camara_votacoes_id.abc": "completeness",
        "test.p.source_unique_camara_votacoes_id.abc": "uniqueness",
        "test.p.dbt_utils_equal_rowcount_disputas_ref_stg_tse__vagas_.abc": "consistency",
        "test.p.candidaturas_sem_votos_carregados": "completeness",
        "test.p.pessoas_perdidas_aos_marts": "consistency",
    }
    assert {uid: health.dimension_of(uid, singular) for uid in expected} == expected
    assert health.dimension_of("test.p.teste_desconhecido.abc", singular) is None


def test_scores_are_pass_100_warn_50_fail_0_averaged_by_dimension_and_overall(con: Connection) -> None:
    build_run(
        con,
        {
            "test.p.not_null_a_x.1": "pass",
            "test.p.not_null_b_x.2": "warn",
            "test.p.unique_a_x.3": "fail",
            "test.p.unique_b_x.4": "pass",
            "test.p.accepted_values_a_x.5": "pass",
        },
    )
    out = "\n".join(health.lines(con))
    assert "completude: 75 (2 testes, 1 avisos, 0 falhas)" in out
    assert "unicidade: 50 (2 testes, 0 avisos, 1 falhas)" in out
    assert "validade: 100 (1 testes, 0 avisos, 0 falhas)" in out
    assert "acurácia: sem testes" in out
    assert "geral 75" in out  # média de 75, 50 e 100 (as dimensões com teste)
    assert "puxa para baixo: [warn] not_null_b_x" in out and "[fail] unique_a_x" in out


def test_the_health_section_is_part_of_the_report_but_never_a_problem_by_itself(con: Connection) -> None:
    build_run(con, {"test.p.not_null_a_x.1": "pass"})
    lines, failed = observability.report(con)
    assert any(line.startswith("Saúde por dimensão") for line in lines)
    assert not failed


def test_without_test_results_the_section_says_so(con: Connection) -> None:
    assert health.lines(con) == ["Saúde por dimensão: sem resultados de teste"]


def test_every_singular_test_in_the_repository_has_a_dimension() -> None:
    folders = [p for p in (DBT_DIR / "tests").iterdir() if p.is_dir()]
    unclassified = [p.name for p in folders if p.name not in health.SINGULAR]
    assert unclassified == [], f"pasta de teste singular sem dimensão em health.SINGULAR: {unclassified}"
    singular = health.singular_tests()
    files = {f.stem for p in folders for f in p.glob("*.sql")}
    assert files == set(singular) and singular


def test_every_test_of_the_last_build_gets_a_dimension(full: tuple[Connection, Settings]) -> None:
    con, _ = full
    rows = con.execute("SELECT DISTINCT unique_id FROM metadata.dbt_results WHERE kind = 'test'").fetchall()
    ids = [r[0] for r in rows]
    assert ids
    singular = health.singular_tests()
    missing = [uid for uid in ids if health.dimension_of(uid, singular) is None]
    assert missing == [], f"testes sem dimensão (acrescente a regra em transformation/health.py): {missing}"
