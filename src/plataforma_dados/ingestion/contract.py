"""Contrato declarativo de uma fonte (`contracts/<fonte>.yml`): de onde vem e o que se carrega."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from plataforma_dados.core.settings import SOURCES_DIR

POWERS = {"legislativo", "executivo", "judiciario"}
LEVELS = {"federal", "estadual", "municipal"}
LOADS = {"full", "yearly"}
PARTITIONS = {"year", "legislature"}
WRITES = {"merge", "replace"}
# Documentos pessoais nunca são lidos de nenhuma fonte (princípio IX da constituição do projeto).
# Chave "linha inteira": identifica a linha pelo conteúdo, para arquivos sem chave natural.
ROW_HASH = "_row_hash"
FORBIDDEN_COLUMNS = {"cpf", "rg", "tituloeleitor", "cnh", "passaporte"}


class InvalidContract(ValueError):
    """O YAML do contrato está errado (a mensagem diz onde)."""


@dataclass(frozen=True)
class Dataset:
    name: str
    url: str
    load: str
    write: str
    columns: tuple[str, ...]
    primary_key: tuple[str, ...] = ()
    stable_after_years: int = 1
    extra_years: bool = False
    first_year: int | None = None
    partition: str = "year"

    @property
    def yearly(self) -> bool:
        return self.load == "yearly"


@dataclass(frozen=True)
class SourceContract:
    source: str
    power: str
    level: str
    description: str
    base_url: str
    delimiter: str
    encoding: str
    datasets: dict[str, Dataset] = field(default_factory=dict)

    def url(self, dataset: str, year: int | None = None) -> str:
        """Endereço oficial do arquivo de um dataset.

        Nos particionados, `year` é o valor da partição: o ano ou, em `partition: legislature`, o
        número da legislatura.
        """
        d = self.datasets[dataset]
        if d.yearly and year is None:
            raise ValueError(f"{dataset} é particionado: informe o ano ou a legislatura")
        return d.url.format(base_url=self.base_url, year=year, legislature=year)

    @property
    def schema(self) -> str:
        """Esquema do raw desta fonte: `raw_<esfera>_<fonte>` (o poder fica no contrato e na pasta)."""
        return f"raw_{self.level}_{self.source}"


def _dataset(source: str, name: str, data: dict[str, Any]) -> Dataset:
    where = f"{source}.{name}"
    for required in ("url", "load", "write", "columns"):
        if required not in data:
            raise InvalidContract(f"{where}: falta '{required}'")
    if data["load"] not in LOADS:
        raise InvalidContract(f"{where}: load '{data['load']}' inválido ({sorted(LOADS)})")
    if data.get("partition", "year") not in PARTITIONS:
        raise InvalidContract(f"{where}: partition '{data['partition']}' inválido ({sorted(PARTITIONS)})")
    if data["write"] not in WRITES:
        raise InvalidContract(f"{where}: write '{data['write']}' inválido ({sorted(WRITES)})")
    columns = tuple(data["columns"])
    for column in columns:
        if column.lower().replace("_", "") in FORBIDDEN_COLUMNS:
            raise InvalidContract(f"{where}: '{column}' é documento pessoal e nunca é lido")
    key = tuple(data.get("primary_key", ()))
    missing = [c for c in key if c not in columns and c != ROW_HASH]
    if missing:
        raise InvalidContract(f"{where}: chave {missing} não está em columns")
    if data["write"] == "merge" and not key:
        raise InvalidContract(f"{where}: write merge exige primary_key")
    return Dataset(
        name=name,
        url=data["url"],
        load=data["load"],
        write=data["write"],
        columns=columns,
        primary_key=key,
        stable_after_years=int(data.get("stable_after_years", 1)),
        extra_years=bool(data.get("extra_years", False)),
        partition=str(data.get("partition", "year")),
        first_year=int(data["first_year"]) if data.get("first_year") is not None else None,
    )


def load_contract(path: Path) -> SourceContract:
    """Lê e valida o contrato de uma fonte."""
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    access = data.get("access", {})
    source = data["source"]
    for field_name, allowed in (("power", POWERS), ("level", LEVELS)):
        if data.get(field_name) not in allowed:
            raise InvalidContract(f"{source}: {field_name} deve ser um de {sorted(allowed)}")
    return SourceContract(
        source=source,
        power=data["power"],
        level=data["level"],
        description=data.get("description", source),
        base_url=access["base_url"],
        delimiter=access.get("delimiter", ";"),
        encoding=access.get("encoding", "utf-8-sig"),
        datasets={n: _dataset(source, n, d) for n, d in data["datasets"].items()},
    )


def find(source: str) -> SourceContract:
    """Contrato de uma fonte, procurado em `sources/<poder>/<esfera>/<fonte>.yml`."""
    for path in SOURCES_DIR.glob(f"*/*/{source}.yml"):
        return load_contract(path)
    raise InvalidContract(f"fonte '{source}' não tem contrato em {SOURCES_DIR}")
