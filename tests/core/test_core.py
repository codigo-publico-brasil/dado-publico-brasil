"""Núcleo: registro de execuções, migrações, modo somente leitura e configuração."""

from pathlib import Path

import duckdb
import pytest

from dado_publico_brasil.core import migrations, runs, warehouse
from dado_publico_brasil.core.settings import Settings, load_settings
from dado_publico_brasil.core.warehouse import Connection


@pytest.fixture
def con(tmp_path: Path) -> Connection:
    """Warehouse novo, só com as migrações do núcleo aplicadas."""
    return migrations.open_warehouse(Settings(storage_root=tmp_path / "store"))


def test_run_records_start_end_counts_and_code_version(con: Connection) -> None:
    with runs.track(con, "load", "camara", "proposicoes", 2024) as run:
        run.rows_in, run.rows_out = 10, 9
    row = con.execute(
        "SELECT stage, source, dataset, year, status, rows_in, rows_out, code_version, finished_at "
        "FROM metadata.runs"
    ).fetchone()
    assert row is not None
    assert row[:7] == ("load", "camara", "proposicoes", 2024, "ok", 10, 9)
    assert row[7] and row[8]


def test_failed_run_is_recorded_and_the_error_is_raised(con: Connection) -> None:
    with pytest.raises(ValueError), runs.track(con, "extract", "camara"):
        raise ValueError("falhou")
    assert con.execute("SELECT status, message FROM metadata.runs").fetchone() == (
        "error",
        "falhou",
    )


def test_migrations_apply_once_and_in_order(tmp_path: Path) -> None:
    con = warehouse.connect(Settings(storage_root=tmp_path / "store"))
    assert migrations.apply(con) == ["0001", "0002", "0003", "0004", "0005"]
    assert migrations.apply(con) == []


def test_reading_in_read_only_mode_refuses_writes(tmp_path: Path) -> None:
    settings = Settings(storage_root=tmp_path / "store")
    migrations.open_warehouse(settings).close()
    con = warehouse.connect(settings, read_only=True)
    with pytest.raises(duckdb.Error):
        con.execute("DELETE FROM metadata.runs")


def test_settings_come_from_the_environment_and_explicit_arguments_win(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("DADO_PUBLICO_STORAGE_ROOT", raising=False)
    monkeypatch.delenv("DADO_PUBLICO_WAREHOUSE", raising=False)
    assert load_settings().storage_root == Path("data_store")
    monkeypatch.setenv("DADO_PUBLICO_STORAGE_ROOT", "from_env")
    monkeypatch.setenv("DADO_PUBLICO_WAREHOUSE", "{root}/my.duckdb")
    settings = load_settings()
    assert settings.warehouse == Path("from_env/my.duckdb")
    assert load_settings(storage_root=Path("explicit")).storage_root == Path("explicit")
