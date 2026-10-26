"""Quando o raw registra atualização no Dagster (e libera dbt, identidade e publicação)."""

from dado_publico_brasil.orchestration.pipeline import registers_update


def test_without_new_data_nothing_downstream_runs() -> None:
    assert not registers_update(captures=0, refresh=False, never_registered=False)


def test_new_captures_release_what_depends_on_the_raw() -> None:
    assert registers_update(captures=2, refresh=False, never_registered=False)


def test_a_refresh_job_rebuilds_even_without_new_data() -> None:
    assert registers_update(captures=0, refresh=True, never_registered=False)


def test_the_first_time_registers_so_the_automation_is_not_blocked_by_a_missing_asset() -> None:
    assert registers_update(captures=0, refresh=False, never_registered=True)
