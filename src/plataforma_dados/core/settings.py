"""Configuração do ambiente: só a pasta de armazenamento e o warehouse, por variável de ambiente.

Fontes: `sources/`. Transformação: `dbt/`. Tabelas próprias: `ddl/`.
"""

import os
from dataclasses import dataclass
from pathlib import Path

ENV_ROOT = "PLATAFORMA_STORAGE_ROOT"
ENV_WAREHOUSE = "PLATAFORMA_WAREHOUSE"
DEFAULT_WAREHOUSE = "{root}/warehouse.duckdb"

REPO_ROOT = Path(__file__).resolve().parents[3]
SOURCES_DIR = REPO_ROOT / "sources"
DBT_DIR = REPO_ROOT / "dbt"
DDL_DIR = REPO_ROOT / "ddl"


@dataclass(frozen=True)
class Settings:
    storage_root: Path = Path("data_store")
    warehouse_template: str = DEFAULT_WAREHOUSE

    @property
    def warehouse(self) -> Path:
        return Path(self.warehouse_template.format(root=self.storage_root))

    @property
    def landing_dir(self) -> Path:
        return self.storage_root / "landing"

    @property
    def state_dir(self) -> Path:
        """Estado local das ferramentas (dlt e dbt), dentro da pasta de armazenamento."""
        return self.storage_root.resolve() / ".state"


def load_settings(storage_root: Path | None = None, warehouse: str | None = None) -> Settings:
    """Argumentos explícitos vencem as variáveis de ambiente, que vencem os padrões."""
    return Settings(
        storage_root=storage_root or Path(os.environ.get(ENV_ROOT, "data_store")),
        warehouse_template=warehouse or os.environ.get(ENV_WAREHOUSE, DEFAULT_WAREHOUSE),
    )
