"""Monitoramento das fontes: disponibilidade, mudança de colunas e queda de volume."""

import urllib.error
from pathlib import Path

from plataforma_dados.core import runs
from plataforma_dados.core.settings import Settings
from plataforma_dados.core.warehouse import Connection
from plataforma_dados.ingestion import landing, monitoring
from plataforma_dados.ingestion.contract import SourceContract


def checks(con: Connection, name: str) -> list[tuple[str, str]]:
    return con.execute(
        "SELECT status, detail FROM metadata.source_checks WHERE check_name = ? ORDER BY id", (name,)
    ).fetchall()


def header_file(tmp_path: Path, columns: list[str], name: str = "f.csv") -> Path:
    file = tmp_path / name
    file.write_text(";".join(columns) + "\n1;A;B\n", encoding="utf-8")
    return file


def test_unavailable_source_is_recorded_and_the_plan_goes_on(
    con: Connection, settings: Settings, contract: SourceContract
) -> None:
    def broken(url: str, folder: Path) -> tuple[Path, str, int]:
        raise urllib.error.HTTPError(url, 404, "Not Found", None, None)  # type: ignore[arg-type]

    result = landing.extract(
        con, settings, contract, "partidos", None, downloader=broken, head_request=lambda url: {}
    )
    assert result == -1
    [(status, detail)] = checks(con, "availability")
    assert status == "error" and "404" in detail


def test_missing_contract_column_is_an_error_and_a_new_column_is_a_warning(
    con: Connection, contract: SourceContract, tmp_path: Path
) -> None:
    dataset = contract.datasets["partidos"]
    columns = list(dataset.columns)
    monitoring.check_header(con, contract, dataset, None, header_file(tmp_path, columns))
    monitoring.check_header(con, contract, dataset, None, header_file(tmp_path, [*columns, "novo"]))
    monitoring.check_header(con, contract, dataset, None, header_file(tmp_path, columns[1:]))
    schema = checks(con, "schema")
    assert [s for s, _ in schema] == ["ok", "warn", "error", "warn"]
    assert "novo" in schema[1][1]
    assert columns[0] in schema[2][1]


def test_volume_drop_against_the_previous_load_is_a_warning(con: Connection) -> None:
    with runs.track(con, "load", "camara", "partidos", None) as run:
        run.rows_in = 100
    monitoring.check_volume(con, "camara", "partidos", None, 90)
    monitoring.check_volume(con, "camara", "partidos", None, 50)
    assert [s for s, _ in checks(con, "volume")] == ["ok", "warn"]
