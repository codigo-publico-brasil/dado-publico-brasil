"""`estado.duckdb` (ADR 0051): `metadata` e `identity` fora do warehouse; migração de quem já tinha os dados dentro."""

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


def test_a_new_warehouse_keeps_metadata_and_identity_in_the_state_file(tmp_path: Path) -> None:
    settings = Settings(storage_root=tmp_path)
    con = migrations.open_warehouse(settings)
    try:
        assert settings.estado == tmp_path / "estado.duckdb" and settings.estado.exists()
        assert scalar(con, IN_WAREHOUSE) == 0
        con.execute(
            "INSERT INTO identity.pessoas (dt_criacao) VALUES ('2026-10-23')"
        )  # nome curto, vai ao estado
        assert scalar(con, "SELECT count(*) FROM estado.identity.pessoas") == 1
        con.execute("CREATE TABLE main.x AS SELECT 1 AS a")  # o resto continua no warehouse
        assert (
            scalar(
                con,
                "SELECT count(*) FROM duckdb_tables() WHERE database_name = 'estado' AND table_name = 'x'",
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
    assert not settings.estado.exists()  # recomeça limpo na próxima subida
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
