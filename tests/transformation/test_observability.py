"""Relatório de saúde dos dados e alerta por e-mail."""

import smtplib
from typing import Any

import pytest

from dado_publico_brasil.core import alert, runs
from dado_publico_brasil.core.warehouse import Connection
from dado_publico_brasil.transformation import observability, quality


def build_run(con: Connection, results: list[dict[str, Any]]) -> None:
    with runs.track(con, "transform_post", "dbt") as run:
        quality.record(con, run.id, results)


def result(unique_id: str, status: str) -> dict[str, Any]:
    return {"unique_id": unique_id, "status": status, "failures": 1, "message": "Got 1 result"}


def test_a_clean_state_is_not_a_problem(con: Connection) -> None:
    build_run(con, [result("test.dado_publico_brasil.not_null_pessoas_id_pessoa.abc", "pass")])
    lines, failed = observability.report(con)
    assert not failed and "Anomalias nos marts (Elementary): 0" in lines


def test_an_elementary_anomaly_is_a_problem_but_a_warning_of_our_own_gap_test_is_not(con: Connection) -> None:
    build_run(
        con,
        [
            result("test.dado_publico_brasil.elementary_volume_anomalies_votos_.abc", "warn"),
            result("test.dado_publico_brasil.autorias_de_proposicao_nao_carregada.abc", "warn"),
        ],
    )
    lines, failed = observability.report(con)
    assert failed
    assert any("elementary_volume_anomalies_votos_" in line for line in lines)
    assert not any("autorias_de_proposicao" in line for line in lines)


def test_a_failing_dbt_test_is_a_problem(con: Connection) -> None:
    build_run(con, [result("test.dado_publico_brasil.unique_pessoas_id_pessoa.abc", "fail")])
    assert observability.report(con)[1]


def test_the_alert_goes_out_only_when_there_is_a_problem(
    con: Connection, monkeypatch: pytest.MonkeyPatch
) -> None:
    sent: list[str] = []

    def send(subject: str, body: str) -> bool:
        sent.append(body)
        return True

    monkeypatch.setattr(alert, "send", send)
    build_run(con, [result("test.dado_publico_brasil.not_null_pessoas_id_pessoa.abc", "pass")])
    assert not observability.notify(con) and not sent
    build_run(con, [result("test.dado_publico_brasil.elementary_schema_changes_pessoas_.abc", "warn")])
    assert observability.notify(con) and "elementary_schema_changes" in sent[0]


def test_an_smtp_failure_does_not_break_the_pipeline(
    con: Connection, monkeypatch: pytest.MonkeyPatch
) -> None:
    def broken(subject: str, body: str) -> bool:
        raise smtplib.SMTPException("fora do ar")

    monkeypatch.setattr(alert, "send", broken)
    build_run(con, [result("test.dado_publico_brasil.unique_pessoas_id_pessoa.abc", "fail")])
    assert observability.notify(con) is False


def test_the_email_needs_smtp_and_a_recipient_and_uses_starttls_with_login(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("DADO_PUBLICO_SMTP_HOST", raising=False)
    assert alert.send("assunto", "corpo") is False
    calls: list[str] = []

    class FakeSMTP:
        def __init__(self, host: str, port: int) -> None:
            calls.append(f"conectou {host}:{port}")

        def __enter__(self) -> "FakeSMTP":
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def starttls(self, context: object) -> None:
            calls.append("starttls")

        def login(self, user: str, password: str) -> None:
            calls.append(f"login {user}")

        def send_message(self, message: Any) -> None:
            calls.append(f"enviou {message['To']} {message['Subject']}")

    monkeypatch.setattr(smtplib, "SMTP", FakeSMTP)
    for key, value in {
        "DADO_PUBLICO_SMTP_HOST": "smtp.exemplo.org",
        "DADO_PUBLICO_SMTP_USER": "alerta@exemplo.org",
        "DADO_PUBLICO_SMTP_PASSWORD": "segredo",
        "DADO_PUBLICO_ALERT_TO": "equipe@exemplo.org",
    }.items():
        monkeypatch.setenv(key, value)
    assert alert.send("assunto", "corpo") is True
    assert calls == [
        "conectou smtp.exemplo.org:587",
        "starttls",
        "login alerta@exemplo.org",
        "enviou equipe@exemplo.org assunto",
    ]
