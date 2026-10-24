"""Monitoramento das fontes: disponibilidade, mudança de colunas e queda de volume."""

import urllib.error
import zipfile
from pathlib import Path

from dado_publico_brasil.core import runs
from dado_publico_brasil.core.settings import Settings
from dado_publico_brasil.core.warehouse import Connection
from dado_publico_brasil.ingestion import landing, monitoring
from dado_publico_brasil.ingestion.contract import SourceContract


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
    assert [s for s, _ in checks(con, "schema")] == ["ok", "ok", "error"]
    changed = checks(con, "schema_mudou")
    assert [s for s, _ in changed] == ["ok", "warn", "warn"]
    assert "novo" in changed[1][1]
    assert columns[0] in checks(con, "schema")[2][1]


def test_volume_drop_against_the_previous_load_is_a_warning(con: Connection) -> None:
    with runs.track(con, "load", "camara", "partidos", None) as run:
        run.rows_in = 100
    monitoring.check_volume(con, "camara", "partidos", None, 90)
    monitoring.check_volume(con, "camara", "partidos", None, 50)
    assert [s for s, _ in checks(con, "volume")] == ["ok", "warn"]


def test_a_different_column_order_is_not_a_schema_change(
    con: Connection, contract: SourceContract, tmp_path: Path
) -> None:
    dataset = contract.datasets["partidos"]
    columns = list(dataset.columns)
    monitoring.check_header(con, contract, dataset, None, header_file(tmp_path, columns))
    monitoring.check_header(con, contract, dataset, None, header_file(tmp_path, columns[::-1], "g.csv"))
    assert [s for s, _ in checks(con, "schema")] == ["ok", "ok"]
    assert [s for s, _ in checks(con, "schema_mudou")] == ["ok", "ok"]


def test_json_that_omits_an_empty_field_is_a_warning_and_csv_missing_a_column_stays_an_error(
    con: Connection, tmp_path: Path
) -> None:
    from dado_publico_brasil.ingestion import contract as contracts

    senado = contracts.find("senado")
    file = tmp_path / "lista.json"
    file.write_text(
        '{"ListaDocumento": {"documentos": {"documento": [{"id": "1", "tipo": "LEI"}]}}}', encoding="utf-8"
    )
    monitoring.check_header(con, senado, senado.datasets["normas"], 1950, file)
    [(status, detail)] = [(s, d) for s, d in checks(con, "schema")]
    assert status == "warn" and "numero" in detail


def test_the_column_change_is_measured_against_the_same_partition_not_against_another_year(
    con: Connection, contract: SourceContract, tmp_path: Path
) -> None:
    dataset = contract.datasets["partidos"]
    columns = list(dataset.columns)
    monitoring.check_header(con, contract, dataset, 2020, header_file(tmp_path, columns))
    monitoring.check_header(con, contract, dataset, 2021, header_file(tmp_path, [*columns, "extra"], "h.csv"))
    assert [s for s, _ in checks(con, "schema_mudou")] == ["ok", "ok"]  # outro ano não é mudança
    monitoring.check_header(con, contract, dataset, 2021, header_file(tmp_path, columns, "i.csv"))
    assert [s for s, _ in checks(con, "schema_mudou")][-1] == "warn"  # o mesmo ano mudou


def test_an_old_name_declared_as_alias_counts_as_the_current_column(con: Connection, tmp_path: Path) -> None:
    from dado_publico_brasil.ingestion import contract as contracts

    tse = contracts.find("tse")
    bens = tse.datasets["bens"]
    legacy = {v: k for k, v in bens.aliases.items()}
    file = tmp_path / "bem_candidato_2006.zip"
    with zipfile.ZipFile(file, "w") as z:
        header = ";".join(legacy.get(c, c) for c in bens.columns)
        row = ";".join("x" for _ in bens.columns)
        z.writestr("bem_candidato_2006_BRASIL.csv", header + chr(10) + row + chr(10))
    monitoring.check_header(con, tse, bens, 2006, file)
    assert [s for s, _ in checks(con, "schema")] == ["ok"]


def test_the_source_health_is_the_worst_of_the_latest_record_of_each_check(con: Connection) -> None:
    assert monitoring.latest_status(con, "camara", "votos") == ("ok", [])
    monitoring.record(con, "camara", "votos", 2024, "availability", "error", "404")
    assert monitoring.latest_status(con, "camara", "votos")[0] == "error"
    monitoring.record(con, "camara", "votos", 2024, "availability", "ok", "100 bytes")  # corrigido
    monitoring.record(con, "camara", "votos", 2023, "volume", "warn", "de 100 para 50 linhas")
    status, details = monitoring.latest_status(con, "camara", "votos")
    assert status == "warn" and details == ["[warn] volume (2023): de 100 para 50 linhas"]
    assert monitoring.latest_status(con, "camara", "outro") == ("ok", [])
