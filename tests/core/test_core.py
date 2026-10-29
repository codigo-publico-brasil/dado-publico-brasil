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
    assert migrations.apply(con) == ["0001", "0002", "0003", "0004", "0005", "0006"]
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


def test_rebuild_carries_only_the_metadata_and_moves_the_sequences_past_the_old_ids(tmp_path: Path) -> None:
    from dado_publico_brasil.core import rebuild

    old = Settings(storage_root=tmp_path / "antigo")
    con = migrations.open_warehouse(old)
    con.execute(
        "INSERT INTO metadata.captures (id, source, dataset, year, url, sha256, size_bytes, path, captured_at, "
        "last_checked_at, loaded_at) VALUES (40, 'camara', 'votacoes', 2024, 'https://x/a', 'abc', 1, 'p', "
        "'2026-10-20', '2026-10-21', '2026-10-22')"
    )
    con.execute("INSERT INTO identity.pessoa VALUES (1, '2026-10-23')")
    con.execute(
        "INSERT INTO metadata.source_checks (id, checked_at, source, dataset, check_name, status, detail) "
        "VALUES (90, '2026-10-21', 'camara', 'votacoes', 'carga', 'ok', 'x')"
    )
    con.close()
    new = Settings(storage_root=tmp_path / "novo")
    dlt = new.state_dir / "dlt"
    dlt.mkdir(parents=True)
    copied = rebuild.start_from(new, old.warehouse)
    assert copied["captures"] == 1 and copied["source_checks"] == 1
    fresh = warehouse.connect(new)
    assert fresh.execute("SELECT id, loaded_at FROM metadata.captures").fetchall() == [
        (40, None)
    ]  # recarrega tudo
    assert fresh.execute("SELECT count(*) FROM identity.pessoa").fetchone() == (0,)  # a identidade não vem
    assert fresh.execute("SELECT nextval('metadata.seq_captures')").fetchone()[0] > 40  # type: ignore[index]
    assert fresh.execute("SELECT nextval('metadata.seq_source_checks')").fetchone()[0] > 90  # type: ignore[index]
    fresh.close()
    assert not dlt.exists() and list(
        new.state_dir.glob("dlt.antes-*")
    )  # o estado do dlt antigo ficou de lado


def test_rebuild_refuses_to_overwrite_a_warehouse_or_start_from_a_missing_one(tmp_path: Path) -> None:
    from dado_publico_brasil.core import rebuild

    existing = Settings(storage_root=tmp_path / "x")
    migrations.open_warehouse(existing).close()
    with pytest.raises(FileExistsError):
        rebuild.start_from(existing, existing.warehouse)
    with pytest.raises(FileNotFoundError):
        rebuild.start_from(Settings(storage_root=tmp_path / "y"), tmp_path / "nao-existe.duckdb")
