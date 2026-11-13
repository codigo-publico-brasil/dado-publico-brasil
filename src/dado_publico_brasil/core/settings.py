"""Configuração do ambiente por variável: pasta de dados e warehouse DuckDB.

Fontes: `sources/`. Transformação: `dbt/`. Tabelas próprias: `ddl/`.
"""

import os
from dataclasses import dataclass
from pathlib import Path

ENV_ROOT = "DADO_PUBLICO_STORAGE_ROOT"
ENV_WAREHOUSE = "DADO_PUBLICO_WAREHOUSE"
DEFAULT_WAREHOUSE = "{root}/warehouse.duckdb"
REGISTRY_ALIAS = "registry"  # alias do arquivo anexado ao warehouse (ADR 0060)
REGISTRY_FILE = f"{REGISTRY_ALIAS}.duckdb"
REGISTRY_LEGADO_FILE = "estado.duckdb"  # nome anterior ao ADR 0060, adotado na primeira abertura

REPO_ROOT = Path(__file__).resolve().parents[3]
SOURCES_DIR = REPO_ROOT / "sources"
DBT_DIR = REPO_ROOT / "dbt"
SITE_DIR = REPO_ROOT / "site"
DDL_DIR = REPO_ROOT / "ddl"


@dataclass(frozen=True)
class Settings:
    storage_root: Path = Path("data_store")
    warehouse_template: str = DEFAULT_WAREHOUSE

    @property
    def warehouse(self) -> Path:
        return Path(self.warehouse_template.format(root=self.storage_root))

    @property
    def registry(self) -> Path:
        """`registry.duckdb`, ao lado do warehouse: `metadata` e `identity` (ADR 0051 e 0060)."""
        return self.warehouse.with_name(REGISTRY_FILE)

    @property
    def dbt_env(self) -> dict[str, str]:
        """Arquivos que o dbt e o `edr` (outros processos) abrem: o warehouse e o registry (só leitura)."""
        return {
            "DADO_PUBLICO_WAREHOUSE_FILE": str(self.warehouse.resolve()),
            "DADO_PUBLICO_REGISTRY_FILE": str(self.registry.resolve()),
        }

    @property
    def landing_dir(self) -> Path:
        return self.storage_root / "landing"

    @property
    def state_dir(self) -> Path:
        """Estado local das ferramentas (dlt e dbt), dentro da pasta de armazenamento."""
        return self.storage_root.resolve() / ".state"


def load_env_file(path: Path | None = None) -> None:
    """Carrega o `.env` (ou `DADO_PUBLICO_ENV_FILE`) no ambiente, sem sobrescrever o que já está definido.

    Sem isto o CLI só via variáveis do shell e, sem as chaves do R2, o `export` gravava só na pasta local.
    """
    path = path or Path(os.environ.get("DADO_PUBLICO_ENV_FILE", ".env"))
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        key, sep, value = line.strip().partition("=")
        if sep and key and not key.startswith("#"):
            os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


def load_settings(storage_root: Path | None = None, warehouse: str | None = None) -> Settings:
    """Argumentos explícitos vencem as variáveis de ambiente, que vencem os padrões."""
    return Settings(
        storage_root=storage_root or Path(os.environ.get(ENV_ROOT, "data_store")),
        warehouse_template=warehouse or os.environ.get(ENV_WAREHOUSE, DEFAULT_WAREHOUSE),
    )
