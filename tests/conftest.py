"""Fixtures: o conjunto sintético da Câmara (formato real, sem rede) roda uma vez e cada teste copia o resultado.

`landed` (arquivos recebidos), `raw` (depois do dlt) e `full` (depois de dbt e identidade).
"""

import shutil
from collections.abc import Iterator
from pathlib import Path

import pytest
from synthetic_camara import fake_downloader, no_headers, synthetic_files
from synthetic_normas import normas_files, normas_get
from synthetic_senado import senado_files
from synthetic_tramitacao import fake_get
from synthetic_transparencia import transparencia_files
from synthetic_tse import tse_files

from plataforma_dados.core import migrations
from plataforma_dados.core.settings import Settings
from plataforma_dados.core.warehouse import Connection
from plataforma_dados.ingestion import contract as contracts
from plataforma_dados.ingestion import landing, loader
from plataforma_dados.ingestion.contract import SourceContract
from plataforma_dados.orchestration import pipeline


@pytest.fixture(scope="session")
def contract() -> SourceContract:
    return contracts.find("camara")


def _open(root: Path) -> tuple[Connection, Settings]:
    settings = Settings(storage_root=root)
    return migrations.open_warehouse(settings), settings


def get_everything(url: str) -> tuple[int, bytes]:
    """Chamadas por item das fontes sintéticas: Câmara e Senado (tramitação, processos) e normas e vetos."""
    status, body = fake_get(url)
    return (status, body) if status != 404 else normas_get(url)


@pytest.fixture(scope="session")
def snapshots(tmp_path_factory: pytest.TempPathFactory, contract: SourceContract) -> dict[str, Path]:
    base = tmp_path_factory.mktemp("snapshots")
    files = synthetic_files(base / "origin")
    items = landing.plan(contract, [2024], [])
    con, settings = _open(base / "raw")
    landing.extract_plan(
        con, settings, contract, items, downloader=fake_downloader(files), head_request=no_headers
    )
    con.close()
    shutil.copytree(base / "raw", base / "landed")
    con, settings = _open(base / "raw")
    loader.load_pending(con, settings, contract)
    con.close()
    pipeline.run_all(
        Settings(storage_root=base / "full"),
        lambda c: landing.plan(c, [2022] if c.source == "tse" else [2024], []),  # TSE: só eleição geral
        downloader=fake_downloader(
            {
                **files,
                **senado_files(base / "origin_senado"),
                **tse_files(base / "origin_tse"),
                **normas_files(base / "origin_normas"),
                **transparencia_files(base / "origin_transparencia"),
            }
        ),
        head_request=no_headers,
        per_item=100,
        get=get_everything,
    )
    return {name: base / name for name in ("landed", "raw", "full")}


def _copy(snapshots: dict[str, Path], name: str, target: Path) -> Iterator[tuple[Connection, Settings]]:
    """Cópia de um snapshot para o teste; some quando o teste acaba (o `full` tem dezenas de MB e são muitos testes)."""
    shutil.copytree(snapshots[name], target / "store")
    env = _open(target / "store")
    yield env
    env[0].close()
    shutil.rmtree(target / "store", ignore_errors=True)


@pytest.fixture
def con(tmp_path: Path) -> Connection:
    """Warehouse novo, só com as migrações aplicadas."""
    return _open(tmp_path / "store")[0]


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(storage_root=tmp_path / "store")


@pytest.fixture
def landed(snapshots: dict[str, Path], tmp_path: Path) -> Iterator[tuple[Connection, Settings]]:
    yield from _copy(snapshots, "landed", tmp_path)


@pytest.fixture
def raw(snapshots: dict[str, Path], tmp_path: Path) -> Iterator[tuple[Connection, Settings]]:
    yield from _copy(snapshots, "raw", tmp_path)


@pytest.fixture
def full(snapshots: dict[str, Path], tmp_path: Path) -> Iterator[tuple[Connection, Settings]]:
    yield from _copy(snapshots, "full", tmp_path)
