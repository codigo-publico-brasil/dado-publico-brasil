"""O sensor `verificacoes_em_erro` avisa uma vez das verificações de ativo em erro, mesmo com a execução em SUCCESS."""

import tempfile
from typing import Any

import pytest
from dagster import (
    AssetCheckResult,
    AssetCheckSeverity,
    DagsterInstance,
    SkipReason,
    asset,
    asset_check,
    build_sensor_context,
    materialize,
)

from dado_publico_brasil.core import alert
from dado_publico_brasil.orchestration.checks_sensor import failed_checks


def _run(instance: DagsterInstance, severity: AssetCheckSeverity, passed: bool) -> None:
    @asset(name="a")
    def a() -> None: ...

    @asset_check(asset=a, name="saude_da_fonte")
    def check() -> AssetCheckResult:
        return AssetCheckResult(passed=passed, severity=severity, metadata={"detalhes": "arquivo vazio"})

    assert materialize([a, check], instance=instance).success


def _tick(instance: DagsterInstance, cursor: str | None) -> tuple[Any, str | None]:
    context = build_sensor_context(instance=instance, cursor=cursor)
    result = failed_checks(context)
    assert isinstance(result, SkipReason)
    return result, context.cursor


def test_warns_once_per_error_and_never_repeats(monkeypatch: pytest.MonkeyPatch) -> None:
    sent: list[list[tuple[str, str, str]]] = []

    def fake(items: list[tuple[str, str, str]], url: str | None = None) -> bool:
        sent.append(items)
        return False

    monkeypatch.setattr(alert, "notify_check_errors", fake)
    instance = DagsterInstance.local_temp(tempfile.mkdtemp())
    _run(instance, AssetCheckSeverity.ERROR, passed=False)
    result, cursor = _tick(instance, None)
    assert "1 verificação" in str(result.skip_message)
    assert sent == [[("a", "saude_da_fonte", "arquivo vazio")]]
    _tick(instance, cursor)
    assert len(sent) == 1  # o cursor evita repetir


def test_ignores_warnings_and_passes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(alert, "notify_check_errors", lambda *a, **k: pytest.fail("não deveria avisar"))
    instance = DagsterInstance.local_temp(tempfile.mkdtemp())
    _run(instance, AssetCheckSeverity.WARN, passed=False)
    _run(instance, AssetCheckSeverity.ERROR, passed=True)
    result, _ = _tick(instance, None)
    assert "nenhuma em erro" in str(result.skip_message)
