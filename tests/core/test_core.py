"""Núcleo: registro de execuções, migrações, modo somente leitura e configuração."""

from datetime import datetime
from pathlib import Path

import duckdb
import pytest

from dado_publico_brasil.core import migrations, runs, warehouse
from dado_publico_brasil.core.settings import DDL_DIR, Settings, load_settings
from dado_publico_brasil.core.warehouse import Connection


@pytest.fixture
def con(tmp_path: Path) -> Connection:
    """Warehouse novo, só com as migrações do núcleo aplicadas."""
    return migrations.open_warehouse(Settings(storage_root=tmp_path / "store"))


def test_run_records_start_end_counts_and_code_version(con: Connection) -> None:
    with runs.track(con, "load", "camara", "proposicoes", 2024) as run:
        run.rows_in, run.rows_out = 10, 9
    row = con.execute(
        "SELECT etapa, fonte, dataset, particao, resultado, qtd_linhas_entrada, qtd_linhas_saida, versao_commit, dt_fim "
        "FROM metadata.execucoes"
    ).fetchone()
    assert row is not None
    assert row[:7] == ("load", "camara", "proposicoes", 2024, "ok", 10, 9)
    assert row[7] and row[8]


def test_failed_run_is_recorded_and_the_error_is_raised(con: Connection) -> None:
    with pytest.raises(ValueError), runs.track(con, "extract", "camara"):
        raise ValueError("falhou")
    assert con.execute("SELECT resultado, mensagem FROM metadata.execucoes").fetchone() == (
        "error",
        "falhou",
    )


def test_migrations_apply_once_and_in_order(tmp_path: Path) -> None:
    con = warehouse.connect(Settings(storage_root=tmp_path / "store"))
    assert migrations.apply(con) == [
        "0001",
        "0002",
        "0003",
        "0004",
        "0005",
        "0006",
        "0007",
        "0008",
        "0009",
        "0010",
    ]
    assert migrations.apply(con) == []


def test_migration_0007_renames_and_retypes_a_warehouse_that_already_has_data(tmp_path: Path) -> None:
    old_ddl = tmp_path / "ddl"
    old_ddl.mkdir()
    for file in sorted(DDL_DIR.glob("000[1-6]_*.sql")):
        (old_ddl / file.name).write_text(file.read_text(encoding="utf-8"), encoding="utf-8")
    con = warehouse.connect(Settings(storage_root=tmp_path / "store"))
    migrations.apply(con, old_ddl)  # o warehouse real: nomes em inglês, instantes em texto
    con.execute(
        "INSERT INTO metadata.runs (stage, started_at, status) VALUES ('load', '2026-10-23T10:00:00+00:00', 'ok')"
    )
    con.execute(
        "INSERT INTO metadata.captures (source, dataset, year, url, sha256, size_bytes, path, captured_at, "
        "last_checked_at, run_id, loaded_at) VALUES ('s', 'd', 2024, 'u', 'h', 5, 'p', "
        "'2026-10-23T10:00:00+00:00', '2026-10-24T10:00:00+00:00', 1, NULL)"
    )
    con.execute(
        "INSERT INTO identity.pessoa VALUES (nextval('identity.seq_pessoa'), '2026-10-23T10:00:00+00:00')"
    )
    con.execute(
        "INSERT INTO identity.pessoa_identificador VALUES ('camara', 'dep', '9', 1, 'oficial', 'x', '2026-10-23T10:00:00+00:00')"
    )
    assert migrations.apply(con) == ["0007", "0008", "0009", "0010"]
    assert migrations.apply(con) == []
    assert con.execute("SELECT id_execucao, etapa, dt_inicio FROM metadata.execucoes").fetchall() == [
        (1, "load", datetime(2026, 10, 23, 10))
    ]
    assert con.execute(
        "SELECT id_captura, particao, qtd_bytes, dt_verificacao FROM metadata.capturas"
    ).fetchall() == [(1, 2024, 5, datetime(2026, 10, 24, 10))]
    assert con.execute("SELECT id_pessoa, dt_criacao FROM identity.pessoas").fetchall() == [
        (1, datetime(2026, 10, 23, 10))
    ]
    assert con.execute("SELECT id_na_fonte, dt_ligacao FROM identity.pessoas_identificadores").fetchall() == [
        ("9", datetime(2026, 10, 23, 10))
    ]
    # as sequências seguem do maior id, com os nomes novos
    assert con.execute(
        "INSERT INTO metadata.execucoes (etapa, dt_inicio, resultado) VALUES ('x', now(), 'ok') RETURNING id_execucao"
    ).fetchone() == (2,)
    assert con.execute("SELECT nextval('identity.seq_pessoas')").fetchone() == (2,)
    assert con.execute("SELECT versao FROM metadata.migracoes ORDER BY 1").fetchall()[-1] == ("0010",)
    # instalação nova chega ao mesmo estado final
    fresh = migrations.open_warehouse(Settings(storage_root=tmp_path / "novo"))
    shape = "SELECT table_name, column_name, data_type FROM duckdb_columns() WHERE schema_name IN ('metadata', 'identity') ORDER BY 1, 2"
    assert fresh.execute(shape).fetchall() == con.execute(shape).fetchall()


def test_a_failure_in_migration_0007_leaves_nothing_half_applied(tmp_path: Path) -> None:
    ddl = tmp_path / "ddl"
    ddl.mkdir()
    for file in sorted(DDL_DIR.glob("000[1-7]_*.sql")):
        (ddl / file.name).write_text(file.read_text(encoding="utf-8"), encoding="utf-8")
    broken = ddl / "0007_nomes_em_portugues.sql"
    good = broken.read_text(encoding="utf-8")
    broken.write_text(good + "\nCOMMENT ON COLUMN metadata.execucoes.nao_existe IS 'x';\n", encoding="utf-8")
    con = warehouse.connect(Settings(storage_root=tmp_path / "store"))
    with pytest.raises(duckdb.Error):
        migrations.apply(con, ddl)  # a falha vem depois das renomeações
    tables = "SELECT table_name FROM duckdb_tables() WHERE schema_name = 'metadata'"
    names = {n for (n,) in con.execute(tables).fetchall()}
    assert {"migrations", "runs"} <= names and not {"migracoes", "execucoes"} & names
    assert con.execute("SELECT max(version) FROM metadata.migrations").fetchone() == ("0006",)
    broken.write_text(good, encoding="utf-8")
    assert migrations.apply(con, ddl) == ["0007"]  # reexecutar funciona
    assert con.execute("SELECT max(versao) FROM metadata.migracoes").fetchone() == ("0007",)


def test_reading_in_read_only_mode_refuses_writes(tmp_path: Path) -> None:
    settings = Settings(storage_root=tmp_path / "store")
    migrations.open_warehouse(settings).close()
    con = warehouse.connect(settings, read_only=True)
    with pytest.raises(duckdb.Error):
        con.execute("DELETE FROM metadata.execucoes")


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
        "INSERT INTO metadata.capturas (id_captura, fonte, dataset, particao, url, sha256, qtd_bytes, caminho, dt_captura, "
        "dt_verificacao, dt_carga) VALUES (40, 'camara', 'votacoes', 2024, 'https://x/a', 'abc', 1, 'p', "
        "'2026-10-20', '2026-10-21', '2026-10-22')"
    )
    con.execute("INSERT INTO identity.pessoas VALUES (1, '2026-10-23 00:00:00')")
    con.execute(
        "INSERT INTO metadata.fontes_verificacoes (id_verificacao, dt_verificacao, fonte, dataset, verificacao, resultado, detalhe) "
        "VALUES (90, '2026-10-21', 'camara', 'votacoes', 'carga', 'ok', 'x')"
    )
    con.close()
    new = Settings(storage_root=tmp_path / "novo")
    dlt = new.state_dir / "dlt"
    dlt.mkdir(parents=True)
    copied = rebuild.start_from(new, old.warehouse)
    assert copied["capturas"] == 1 and copied["fontes_verificacoes"] == 1
    fresh = warehouse.connect(new)
    assert fresh.execute("SELECT id_captura, dt_carga FROM metadata.capturas").fetchall() == [
        (40, None)
    ]  # recarrega tudo
    assert fresh.execute("SELECT count(*) FROM identity.pessoas").fetchone() == (0,)  # a identidade não vem
    assert fresh.execute("SELECT nextval('metadata.seq_capturas')").fetchone()[0] > 40  # type: ignore[index]
    assert fresh.execute("SELECT nextval('metadata.seq_fontes_verificacoes')").fetchone()[0] > 90  # type: ignore[index]
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


def test_code_version_prefers_the_image_variable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DADO_PUBLICO_GIT_SHA", "abc1234")
    runs.code_version.cache_clear()
    assert runs.code_version() == "abc1234"
    runs.code_version.cache_clear()
