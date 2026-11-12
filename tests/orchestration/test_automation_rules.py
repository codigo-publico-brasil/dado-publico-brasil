"""Quando o raw registra atualização no Dagster e como o ciclo noturno (ADR 0042) decide rodar e se encaixa."""

from datetime import UTC, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from croniter import croniter  # type: ignore[import-untyped]
from dagster import DagsterInstance, DagsterRun, DagsterRunStatus

from dado_publico_brasil.core.runs import TIMEZONE
from dado_publico_brasil.ingestion import contract
from dado_publico_brasil.orchestration.pipeline import (
    CYCLE_CRON,
    done_today,
    needs_cycle,
    registers_update,
)

ROOT = Path(__file__).resolve().parents[2]


def _minutes(cron: str) -> int:
    fields = cron.split()
    return int(fields[1]) * 60 + int(fields[0])


def test_without_new_data_nothing_downstream_runs() -> None:
    assert not registers_update(captures=0, refresh=False, never_registered=False)


def test_new_captures_release_what_depends_on_the_raw() -> None:
    assert registers_update(captures=2, refresh=False, never_registered=False)


def test_a_refresh_job_rebuilds_even_without_new_data() -> None:
    assert registers_update(captures=0, refresh=True, never_registered=False)


def test_the_first_time_registers_so_the_automation_is_not_blocked_by_a_missing_asset() -> None:
    assert registers_update(captures=0, refresh=False, never_registered=True)


def test_every_source_is_captured_at_night_between_01_and_0330() -> None:
    scheduled = [s for s in contract.find_all() if s.schedule]
    assert scheduled
    for s in scheduled:
        assert croniter.is_valid(str(s.schedule)), s.source
        assert 60 <= _minutes(str(s.schedule)) <= 3 * 60 + 30, (s.source, s.schedule)


def test_the_cycle_runs_after_the_last_capture_with_room_to_finish_it() -> None:
    assert croniter.is_valid(CYCLE_CRON)
    last = max(_minutes(str(s.schedule)) for s in contract.find_all() if s.schedule)
    assert _minutes(CYCLE_CRON) >= last + 60


def test_the_cycle_is_skipped_only_when_nothing_arrived_since_the_last_complete_cycle() -> None:
    assert needs_cycle(raw=[100.0, 90.0], cycle=[120.0, 130.0]) is False
    assert needs_cycle(raw=[100.0, 125.0], cycle=[120.0, 130.0]) is True  # raw novo
    assert (
        needs_cycle(raw=[100.0], cycle=[120.0, 90.0]) is True
    )  # um passo do ciclo não terminou depois do raw
    assert needs_cycle(raw=[100.0], cycle=[120.0, None]) is True  # publicação nunca feita
    assert needs_cycle(raw=[None, None], cycle=[None]) is True  # primeira vez
    assert needs_cycle(raw=[None], cycle=[120.0]) is False


def _run(instance: DagsterInstance, job: str, status: DagsterRunStatus) -> None:
    instance.add_run(DagsterRun(job_name=job, run_id=f"{job}-{status.value}", status=status))


def test_a_success_today_skips_the_schedule_but_a_failure_or_nothing_runs_again() -> None:
    instance = DagsterInstance.ephemeral()
    assert not done_today(instance, "captura_x")  # nada
    _run(instance, "captura_x", DagsterRunStatus.FAILURE)
    assert not done_today(instance, "captura_x")  # só falhou: tenta de novo
    _run(instance, "captura_y", DagsterRunStatus.SUCCESS)
    assert not done_today(instance, "captura_x")  # sucesso de outro job não conta
    _run(instance, "captura_x", DagsterRunStatus.SUCCESS)
    assert done_today(instance, "captura_x")
    _run(instance, "captura_z", DagsterRunStatus.STARTED)
    assert done_today(
        instance, "captura_z"
    )  # em andamento ou na fila também conta (tiques recuperados em sequência)
    tomorrow = datetime.now(UTC) + timedelta(days=1)
    assert not done_today(instance, "captura_x", tomorrow)  # no dia seguinte, roda de novo
    # à noite (21h-24h locais) o Dagster lia a meia-noite local como UTC e errava o dia: vale em qualquer hora
    local_tomorrow = (datetime.now(ZoneInfo(TIMEZONE)) + timedelta(days=1)).replace(hour=22)
    assert not done_today(instance, "captura_x", local_tomorrow)


def test_the_publication_only_leaves_through_the_cycle_job_and_the_manual_job() -> None:
    src = (ROOT / "src/dado_publico_brasil/orchestration/definitions.py").read_text(encoding="utf-8")
    assert "automation_condition" not in src and "AutomationCondition" not in src
    assert "propagar_atualizacoes" not in src


def test_step_logs_start_end_and_failure_in_the_dagster_log() -> None:
    from types import SimpleNamespace

    import pytest

    from dado_publico_brasil.orchestration.pipeline import step

    lines: list[str] = []
    context = SimpleNamespace(log=SimpleNamespace(info=lines.append, error=lines.append))
    with step(context, "passo"):
        pass
    with pytest.raises(ValueError), step(context, "outro"):
        raise ValueError
    assert [x.split(": ")[0] for x in lines] == ["passo", "passo", "outro", "outro"]
    assert "iniciando" in lines[0] and "concluído em" in lines[1] and "falhou" in lines[3]
