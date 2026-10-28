"""Relatório de saúde dos dados e alerta por e-mail."""

import smtplib
import subprocess
from pathlib import Path
from typing import Any

import pytest

from dado_publico_brasil.core import alert, runs
from dado_publico_brasil.core.settings import DBT_DIR, Settings
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
    anomalies = lines[: next(i for i, line in enumerate(lines) if line.startswith("Saúde por dimensão"))]
    assert not any("autorias_de_proposicao" in line for line in anomalies)


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


def test_the_html_report_runs_edr_through_uvx_in_the_state_folder_and_needs_uv(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("shutil.which", lambda name: None)
    with pytest.raises(RuntimeError, match="uvx"):
        observability.html_report(settings)
    called: dict[str, Any] = {}

    def fake_run(command: list[str], **kwargs: Any) -> None:
        called.update(command=command, **kwargs)

    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/uvx")
    monkeypatch.setattr(subprocess, "run", fake_run)
    file = observability.html_report(settings)
    assert file == settings.state_dir / "observabilidade" / "report.html"
    assert called["command"][:5] == [
        "/usr/bin/uvx",
        "--from",
        "elementary-data[duckdb]==0.26.1",
        "edr",
        "report",
    ]
    assert called["command"][5:] == ["--profiles-dir", str(DBT_DIR), "--file-path", str(file)]
    assert called["cwd"] == file.parent  # o edr cria `edr_target` na pasta de trabalho
    assert called["env"]["DADO_PUBLICO_WAREHOUSE_FILE"] == str(settings.warehouse.resolve())


def test_the_email_can_carry_the_html_report(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    sent: list[Any] = []

    class FakeSMTP:
        def __init__(self, host: str, port: int) -> None:
            pass

        def __enter__(self) -> "FakeSMTP":
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def starttls(self, context: object) -> None:
            pass

        def send_message(self, message: Any) -> None:
            sent.append(message)

    monkeypatch.setattr(smtplib, "SMTP", FakeSMTP)
    monkeypatch.setenv("DADO_PUBLICO_SMTP_HOST", "smtp.exemplo.org")
    monkeypatch.setenv("DADO_PUBLICO_ALERT_TO", "equipe@exemplo.org")
    monkeypatch.delenv("DADO_PUBLICO_SMTP_USER", raising=False)
    report = tmp_path / "report.html"
    report.write_text("<html>relatório</html>", encoding="utf-8")
    assert alert.send("assunto", "corpo", report) is True
    [attachment] = list(sent[0].iter_attachments())
    assert attachment.get_filename() == "report.html" and b"relat" in attachment.get_payload(decode=True)


def test_a_failed_run_sends_one_email_with_the_steps_and_the_link_and_a_broken_smtp_does_not_raise(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sent: list[tuple[str, str]] = []

    def send(subject: str, body: str, attachment: Path | None = None) -> bool:
        sent.append((subject, body))
        return True

    monkeypatch.setattr(alert, "send", send)
    assert alert.notify_failure(
        "daily_pipeline", "abc123", ["raw_camara", "dbt"], "Passos falharam", "http://x/runs/abc123"
    )
    subject, body = sent[0]
    assert "daily_pipeline" in subject
    assert "raw_camara, dbt" in body and "Execução: http://x/runs/abc123" in body

    def broken(subject: str, body: str, attachment: Path | None = None) -> bool:
        raise smtplib.SMTPException("fora do ar")

    monkeypatch.setattr(alert, "send", broken)
    assert alert.notify_failure("daily_pipeline", "abc123", [], "x") is False


def capture(con: Connection, dataset: str, checked_at: str) -> None:
    con.execute(
        "INSERT INTO metadata.captures (source, dataset, year, url, sha256, size_bytes, path, captured_at, "
        "last_checked_at) VALUES ('camara', ?, 2024, 'https://x/' || ?, 'abc', 1, 'p', ?, ?)",
        (dataset, dataset, checked_at, checked_at),
    )


def test_a_dataset_not_verified_for_longer_than_its_limit_is_a_problem(con: Connection) -> None:
    capture(con, "votacoes", "2020-01-01T00:00:00")
    lines, failed = observability.report(con, {("camara", "votacoes"): 3})
    assert failed
    assert any("camara.votacoes: última verificação há" in line and "limite de 3" in line for line in lines)


def test_a_recently_verified_dataset_is_not_a_problem(con: Connection) -> None:
    capture(con, "votacoes", runs.now())
    lines, failed = observability.report(con, {("camara", "votacoes"): 3})
    assert not failed and "Capturas velhas: 0" in lines


def test_a_dataset_with_a_limit_and_no_capture_is_a_problem(con: Connection) -> None:
    lines, failed = observability.report(con, {("camara", "proposicoes"): 3})
    assert failed and any("camara.proposicoes: nunca capturado" in line for line in lines)


def test_without_limits_the_stale_check_does_not_run(con: Connection) -> None:
    capture(con, "votacoes", "2020-01-01T00:00:00")
    assert not observability.report(con)[1]
