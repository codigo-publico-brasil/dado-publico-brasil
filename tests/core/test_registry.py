"""`registry.duckdb` (ADR 0051): `metadata` e `identity` fora do warehouse; migração de quem já tinha os dados dentro."""

from pathlib import Path

import duckdb
import legacy_warehouse
import pytest

from dado_publico_brasil.core import migrations, warehouse
from dado_publico_brasil.core.settings import Settings
from dado_publico_brasil.core.warehouse import scalar

IN_WAREHOUSE = (
    "SELECT count(*) FROM duckdb_tables() WHERE database_name = current_database() "
    "AND schema_name IN ('metadata', 'identity')"
)


def test_a_new_warehouse_keeps_metadata_and_identity_in_the_registry_file(tmp_path: Path) -> None:
    settings = Settings(storage_root=tmp_path)
    con = migrations.open_warehouse(settings)
    try:
        assert settings.registry == tmp_path / "registry.duckdb" and settings.registry.exists()
        assert scalar(con, IN_WAREHOUSE) == 0
        con.execute(
            "INSERT INTO identity.pessoas (dt_criacao) VALUES ('2026-10-23')"
        )  # nome curto, vai ao estado
        assert scalar(con, "SELECT count(*) FROM registry.identity.pessoas") == 1
        con.execute("CREATE TABLE main.x AS SELECT 1 AS a")  # o resto continua no warehouse
        assert (
            scalar(
                con,
                "SELECT count(*) FROM duckdb_tables() WHERE database_name = 'registry' AND table_name = 'x'",
            )
            == 0
        )
    finally:
        con.close()


def test_a_read_only_connection_sees_the_state(tmp_path: Path) -> None:
    settings = Settings(storage_root=tmp_path)
    migrations.open_warehouse(settings).close()
    con = warehouse.connect(settings, read_only=True)
    try:
        assert scalar(con, "SELECT count(*) FROM metadata.capturas") == 0
    finally:
        con.close()


def test_legacy_warehouse_moves_its_state_and_keeps_the_rest(tmp_path: Path) -> None:
    settings = Settings(storage_root=tmp_path)
    legacy_warehouse.make(settings)
    con = migrations.open_warehouse(settings)
    try:
        assert scalar(con, IN_WAREHOUSE) == 0  # saiu do warehouse
        assert scalar(con, "SELECT count(*) FROM raw_x.t") == 1  # o raw ficou
        assert scalar(con, "SELECT id_captura FROM metadata.capturas") == 40
        assert scalar(con, "SELECT dt_carga FROM metadata.capturas") is not None  # a cópia é fiel
        assert scalar(con, "SELECT id_pessoa FROM identity.pessoas") == 7
        assert scalar(con, "SELECT nextval('identity.seq_pessoas')") > 7  # chave nunca reaproveitada
        assert scalar(con, "SELECT nextval('metadata.seq_capturas')") > 40
    finally:
        con.close()
    again = migrations.open_warehouse(settings)  # idempotente
    try:
        assert scalar(again, "SELECT count(*) FROM metadata.capturas") == 1
    finally:
        again.close()


def test_a_copy_that_differs_from_the_source_leaves_the_warehouse_untouched(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = Settings(storage_root=tmp_path)
    legacy_warehouse.make(settings)
    real = migrations._fingerprint
    monkeypatch.setattr(
        migrations,
        "_fingerprint",
        lambda con, source, table, cols: (
            *real(con, source, table, cols)[:1],
            1 if source == "legado.metadata." else 0,
        ),
    )
    with pytest.raises(RuntimeError, match="cópia diferente"):
        migrations.open_warehouse(settings)
    assert not settings.registry.exists()  # recomeça limpo na próxima subida
    con = duckdb.connect(str(settings.warehouse), read_only=True)
    try:
        assert scalar(con, "SELECT count(*) FROM metadata.capturas") == 1
        assert scalar(con, "SELECT count(*) FROM identity.pessoas") == 1
    finally:
        con.close()


def test_rebuild_keeps_an_existing_state_and_only_reloads_the_captures(tmp_path: Path) -> None:
    from dado_publico_brasil.core import rebuild

    settings = Settings(storage_root=tmp_path)
    legacy_warehouse.make(settings)
    migrations.open_warehouse(settings).close()
    settings.warehouse.rename(tmp_path / "warehouse.antigo.duckdb")  # o warehouse se refaz, o estado fica
    assert rebuild.start_from(settings)["capturas"] == 1
    con = warehouse.connect(settings)
    try:
        assert con.execute("SELECT id_captura, dt_carga FROM metadata.capturas").fetchall() == [(40, None)]
        assert scalar(con, "SELECT count(*) FROM identity.pessoas") == 1  # a identidade segue
    finally:
        con.close()


def _old_ledger(settings: Settings) -> None:
    """Um registro com dados, como o de produção, sob o nome anterior ao ADR 0060."""
    con = migrations.open_warehouse(settings, restore=False)
    con.execute(
        "INSERT INTO metadata.capturas (id_captura, fonte, dataset, particao, url, sha256, qtd_bytes, caminho, "
        "dt_captura, dt_verificacao) SELECT 100 + i, 'fonte_a', 'conjunto', 2024, 'https://x/' || i, 'h' || i, 1, 'p', '2026-10-20', '2026-10-21' "
        "FROM range(5) t(i)"
    )
    con.execute(
        "INSERT INTO identity.pessoas (id_pessoa, dt_criacao) SELECT i + 1, '2026-01-01' FROM range(3) t(i)"
    )
    con.execute("CHECKPOINT")
    con.close()
    settings.registry.rename(settings.registry.with_name("estado.duckdb"))
    settings.warehouse.unlink()


def _fingerprint(path: Path) -> tuple[int, int, int, int]:
    con = duckdb.connect(str(path), read_only=True)
    try:
        c = con.execute("SELECT count(*), sum(hash(sha256)) FROM metadata.capturas").fetchone()
        p = con.execute("SELECT count(*), sum(hash(id_pessoa)) FROM identity.pessoas").fetchone()
        assert c and p
        return (c[0], int(c[1]), p[0], int(p[1]))
    finally:
        con.close()


def test_the_old_state_file_is_renamed_without_copying(tmp_path: Path) -> None:
    settings = Settings(storage_root=tmp_path)
    _old_ledger(settings)
    old = tmp_path / "estado.duckdb"
    before = _fingerprint(old)
    migrations.adopt_registry(settings)
    assert not old.exists() and settings.registry.exists()
    assert _fingerprint(settings.registry) == before
    con = migrations.open_warehouse(settings)  # abrir de novo não muda nada
    con.close()
    assert not old.exists() and _fingerprint(settings.registry) == before


def test_with_both_files_the_new_one_wins_and_the_old_is_untouched(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    settings = Settings(storage_root=tmp_path)
    _old_ledger(settings)
    duckdb.connect(str(settings.registry)).close()
    old = tmp_path / "estado.duckdb"
    size = old.stat().st_size
    with caplog.at_level("WARNING"):
        migrations.adopt_registry(settings)
    assert old.exists() and old.stat().st_size == size and "usando registry.duckdb" in caplog.text


def test_only_the_new_file_needs_nothing_and_no_empty_registry_is_made_over_the_old(tmp_path: Path) -> None:
    settings = Settings(storage_root=tmp_path)
    migrations.open_warehouse(settings).close()
    assert settings.registry.exists() and not (tmp_path / "estado.duckdb").exists()
    other = Settings(storage_root=tmp_path / "x")
    _old_ledger(other)
    before = _fingerprint(other.registry.with_name("estado.duckdb"))
    migrations.open_warehouse(other, restore=False).close()
    assert _fingerprint(other.registry) == before and not other.registry.with_name("estado.duckdb").exists()
