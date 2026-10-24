"""Testes do dbt de ponta a ponta: resultado gravado e falha que interrompe a transformação."""

import pytest

from dado_publico_brasil.core.settings import Settings
from dado_publico_brasil.core.warehouse import Connection, scalar
from dado_publico_brasil.transformation import build


def failures(con: Connection, test_name: str) -> int | None:
    row = con.execute(
        "SELECT failures FROM metadata.dbt_results WHERE kind = 'test' AND unique_id LIKE ? "
        "ORDER BY recorded_at DESC LIMIT 1",
        (f"test.dado_publico_brasil.{test_name}%",),
    ).fetchone()
    assert row is not None, test_name
    return None if row[0] is None else int(row[0])


def test_known_gaps_are_recorded_as_warnings_with_their_size(
    full: tuple[Connection, Settings],
) -> None:
    con, _ = full
    assert failures(con, "proposicoes_sem_situacao") == 1
    assert failures(con, "autorias_de_proposicao_nao_carregada") == 1
    assert failures(con, "votacoes_com_total_sim_divergente") == 1
    assert failures(con, "votacoes_sem_voto_individual") == 0
    assert failures(con, "pessoas_com_nome_em_maiusculas") == 0
    status = scalar(
        con,
        "SELECT status FROM metadata.dbt_results WHERE unique_id LIKE 'test.dado_publico_brasil.proposicoes_sem_situacao%'",
    )
    assert status == "warn"


def test_no_dbt_test_failed_and_every_model_was_built(full: tuple[Connection, Settings]) -> None:
    con, _ = full
    assert scalar(con, "SELECT COUNT(*) FROM metadata.dbt_results WHERE status IN ('error', 'fail')") == 0
    assert scalar(con, "SELECT COUNT(*) FROM metadata.dbt_results WHERE kind = 'model'") >= 25


def test_a_failing_dbt_test_stops_the_pipeline(full: tuple[Connection, Settings]) -> None:
    con, settings = full
    con.execute("DELETE FROM identity.pessoa_identificador WHERE source_id = '10'")
    con.close()
    with pytest.raises(build.DbtFailure):
        build.transform(settings, "transform_post", *build.POST_IDENTITY)
