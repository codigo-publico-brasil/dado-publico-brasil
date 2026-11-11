"""Bucket privado (ADR 0036): o bucket é uma pasta temporária; o caminho é o mesmo do R2 menos a rede."""

import shutil
from pathlib import Path

import pytest
from synthetic_camara import fake_downloader, no_headers, synthetic_files

from dado_publico_brasil.core import migrations, privado, rebuild
from dado_publico_brasil.core.settings import Settings
from dado_publico_brasil.core.warehouse import Connection, scalar
from dado_publico_brasil.ingestion import landing
from dado_publico_brasil.ingestion.contract import SourceContract
from dado_publico_brasil.transformation import snapshot


@pytest.fixture
def bucket(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    folder = tmp_path / "bucket"
    monkeypatch.setattr(privado, "root", lambda settings: folder.as_posix())
    return folder


def add_person(con: Connection) -> None:
    con.execute("INSERT INTO identity.pessoas (dt_criacao) VALUES ('2026-10-23')")


def test_snapshot_and_metadata_go_to_the_bucket_with_the_marker_last(
    con: Connection, settings: Settings, bucket: Path
) -> None:
    add_person(con)
    folder = snapshot.take(con, settings)
    privado.push_metadata(con, settings)
    assert folder is not None and (Path(folder) / "_concluido").exists()
    assert {f.name for f in (bucket / "metadata").glob("*.parquet")} == {
        f"{t}.parquet" for t in rebuild.TABLES
    }
    assert not (settings.storage_root / "snapshots").exists()  # nada local
    assert snapshot.problems(con, settings) == []


def test_a_snapshot_without_the_marker_is_ignored(con: Connection, settings: Settings, bucket: Path) -> None:
    add_person(con)
    good = snapshot.take(con, settings)
    add_person(con)
    broken = snapshot.take(con, settings)
    assert good and broken and good != broken
    (Path(broken) / "_concluido").unlink()  # envio interrompido
    assert privado.latest(con, settings) == good


def test_the_lock_refuses_to_overwrite_with_fewer_captures(
    con: Connection, settings: Settings, bucket: Path
) -> None:
    con.execute(
        "INSERT INTO metadata.capturas (id_captura, fonte, dataset, particao, url, sha256, qtd_bytes, caminho, "
        "dt_captura, dt_verificacao) VALUES (1, 'camara', 'x', 2024, 'https://x/a', 'abc', 1, 'p', "
        "'2026-10-20', '2026-10-21')"
    )
    privado.push_metadata(con, settings)
    con.execute("DELETE FROM metadata.capturas")
    with pytest.raises(RuntimeError, match="restaure antes"):
        privado.push_metadata(con, settings)
    assert (
        scalar(con, f"SELECT count(*) FROM read_parquet('{bucket.as_posix()}/metadata/capturas.parquet')")
        == 1
    )


def test_an_empty_machine_gets_the_same_keys_and_captures_back(
    con: Connection, settings: Settings, bucket: Path, contract: SourceContract, tmp_path: Path
) -> None:
    download = fake_downloader(synthetic_files(tmp_path / "origin"))
    landing.extract(con, settings, contract, "deputados", downloader=download, head_request=no_headers)
    add_person(con)
    add_person(con)
    snapshot.take(con, settings)
    privado.push_metadata(con, settings)
    people = con.execute("SELECT id_pessoa FROM identity.pessoas ORDER BY 1").fetchall()
    captures = con.execute("SELECT id_captura, sha256, caminho FROM metadata.capturas ORDER BY 1").fetchall()
    con.close()
    shutil.rmtree(settings.storage_root)  # a máquina inteira se perde
    fresh = migrations.open_warehouse(settings)
    assert fresh.execute("SELECT id_pessoa FROM identity.pessoas ORDER BY 1").fetchall() == people
    assert (
        fresh.execute("SELECT id_captura, sha256, caminho FROM metadata.capturas ORDER BY 1").fetchall()
        == captures
    )
    assert scalar(fresh, "SELECT count(*) FROM metadata.capturas WHERE dt_carga IS NOT NULL") == 0
    assert scalar(fresh, "SELECT nextval('identity.seq_pessoas')") > max(p[0] for p in people)
    assert scalar(fresh, "SELECT nextval('metadata.seq_capturas')") > max(c[0] for c in captures)
    assert snapshot.take(fresh, settings) is None  # a identidade restaurada é a mesma: nada novo
    fresh.close()


def test_rebuild_without_the_old_warehouse_restores_from_the_bucket(
    con: Connection, settings: Settings, bucket: Path, tmp_path: Path
) -> None:
    add_person(con)
    snapshot.take(con, settings)
    privado.push_metadata(con, settings)
    con.close()
    new = Settings(storage_root=tmp_path / "novo")
    rebuild.start_from(new)
    again = migrations.open_warehouse(new)
    assert scalar(again, "SELECT count(*) FROM identity.pessoas") == 1
    again.close()


def test_extract_brings_back_a_file_that_vanished_to_the_same_path(
    con: Connection, settings: Settings, contract: SourceContract, tmp_path: Path
) -> None:
    download = fake_downloader(synthetic_files(tmp_path / "origin"))
    first = landing.extract(
        con, settings, contract, "deputados", downloader=download, head_request=no_headers
    )
    path = settings.storage_root / str(scalar(con, "SELECT caminho FROM metadata.capturas"))
    path.unlink()
    again = landing.extract(
        con, settings, contract, "deputados", downloader=download, head_request=no_headers
    )
    assert again == first and path.exists()
    assert scalar(con, "SELECT count(*) FROM metadata.capturas") == 1


def test_a_failed_restore_on_a_new_warehouse_removes_the_file(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    def boom(con: Connection, settings: Settings) -> None:
        raise RuntimeError("R2 fora do ar")

    monkeypatch.setattr(privado, "restore", boom)
    with pytest.raises(RuntimeError, match="R2 fora do ar"):
        migrations.open_warehouse(settings)
    assert not settings.estado.exists()  # senão a próxima subida pularia a restauração
