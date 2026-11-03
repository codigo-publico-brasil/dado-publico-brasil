"""Declaração de uma fonte (`sources/<poder>/<esfera>/<fonte>.yml`): de onde vem e o que se carrega.

O código que só aquela fonte precisa (ver `fetch.py` e `read.py`) fica em
`ingestion/custom/<poder>/<esfera>/<fonte>.py`, espelhando a árvore das declarações."""

import importlib
import re
import string
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType
from typing import Any

import yaml

from dado_publico_brasil.core.settings import SOURCES_DIR

FORMATS = {
    "csv",
    "json",
    "html",
    "members",
}  # html não tem leitor padrão: exige `records` no módulo próprio da fonte
POWERS = {"legislativo", "executivo", "judiciario"}
LEVELS = {"federal", "estadual", "municipal"}
LOADS = {"full", "yearly", "foreach"}
ARCHIVES = {"zip"}
PARTITIONS = {"year", "legislature", "month"}  # month: o valor da partição é AAAAMM
WRITES = {"merge", "replace"}
# Documentos pessoais nunca são lidos de nenhuma fonte (princípio IX da constituição do projeto).
# Chave "linha inteira": identifica a linha pelo conteúdo, para arquivos sem chave natural.
ROW_HASH = "_row_hash"
ITEM = "_item"  # nos datasets `foreach`: o item que deu origem à linha
IDENTIFIER = re.compile(r"^\w+$")
FORBIDDEN_COLUMNS = {"cpf", "rg", "tituloeleitor", "cnh", "passaporte"}


class InvalidContract(ValueError):
    """O YAML do contrato está errado (a mensagem diz onde)."""


@dataclass(frozen=True)
class ForEach:
    """Dataset por item: uma chamada para cada linha de outro dataset da mesma fonte (já no raw)."""

    source: str  # dataset que dá os itens
    item: str  # coluna do raw que vai em {item} na URL
    where: str = "true"  # filtro SQL sobre o raw do dataset de origem
    recent_by: str | None = None  # coluna: os itens mais recentes primeiro (amostras e cargas limitadas)
    version: str | None = None  # coluna: se mudar depois da busca, o item é buscado de novo
    refresh_after_days: int | None = None  # busca de novo depois de N dias
    batch_size: int = 500  # itens por arquivo de lote no landing


@dataclass(frozen=True)
class Arquivos:
    """Como materializar os arquivos de um dataset e se vão ao lake público (ADR 0037).

    Sem `membro`, o arquivo da captura é copiado como está; com `membro`, cada membro do zip que casa com o
    padrão (grupos nomeados viram campos de `caminho`) é extraído. Campos de `caminho`: `dataset`, `particao`
    e `nome`."""

    colecao: str  # a pasta é `arq_<colecao>`
    caminho: str  # modelo do caminho relativo à pasta da coleção
    membro: str | None = None  # regex do nome do membro dentro do zip
    publicar: bool = False  # true: vai ao lake público; false: fica só no disco local


@dataclass(frozen=True)
class Dataset:
    name: str
    url: str
    load: str
    write: str
    columns: tuple[str, ...]
    primary_key: tuple[str, ...] = ()
    extra_years: bool = False
    first_year: int | None = None
    partition: str = "year"
    records: str | None = None  # JSON: caminho (com pontos) da lista de registros
    nested: tuple[str, ...] = ()  # JSON: campos que são listas (viram tabelas filhas no raw)
    format: str | None = None  # sobrepõe `access.format` neste dataset
    headers: dict[str, str] | None = None  # somam-se aos de `access.headers`
    foreach: ForEach | None = None
    archive: str | None = None  # "zip": o arquivo guardado é um pacote; `member` diz qual membro ler
    member: str = "*"  # padrão (glob) do nome do membro dentro do pacote
    raw: bool = True  # false: só o landing (arquivos guardados para uso futuro), sem tabela no raw
    arquivos: Arquivos | None = None  # arquivos servidos ao público, em coleção `arq_` (ADR 0037)
    first_month: int | None = None  # (partition: month) primeiro mês pedido, como AAAAMM
    step: int = 1  # (yearly) só os anos a cada N a partir de first_year (eleições gerais: 4)
    only: dict[str, tuple[str, ...]] = field(default_factory=dict)  # minimização: só linhas com estes valores
    optional: tuple[str, ...] = ()  # colunas que só existem em anos recentes: ausentes não são erro
    aliases: dict[str, str] = field(
        default_factory=dict
    )  # layout antigo: nome antigo da coluna -> nome em `columns`
    max_age_days: int | None = (
        None  # idade máxima da última verificação da fonte; mais velha que isso é problema
    )

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
    format: str = "csv"
    headers: dict[str, str] = field(default_factory=dict)  # aceita ${VARIAVEL} do ambiente
    rate_limit: float = 4.0  # requisições por segundo a toda a fonte (cortesia)
    schedule: str | None = None  # cron (5 campos) da captura automática; None: só quando pedido
    custom: ModuleType | None = None
    datasets: dict[str, Dataset] = field(default_factory=dict)

    def url(self, dataset: str, year: int | None = None) -> str:
        """Endereço oficial do arquivo de um dataset.

        Nos particionados, `year` é o valor da partição: o ano, em `partition: legislature` o
        número da legislatura e em `partition: month` o mês (AAAAMM); `{month}` na URL é esse valor.
        """
        d = self.datasets[dataset]
        if d.yearly and year is None:
            raise ValueError(f"{dataset} é particionado: informe o ano ou a legislatura")
        return d.url.format(base_url=self.base_url, year=year, legislature=year, month=year, item=year)

    def item_url(self, dataset: str, item: str) -> str:
        """Endereço de um item de um dataset `foreach`."""
        return self.datasets[dataset].url.format(base_url=self.base_url, item=item)

    def format_of(self, dataset: str) -> str:
        return self.datasets[dataset].format or self.format

    def headers_of(self, dataset: str) -> dict[str, str]:
        return {**self.headers, **(self.datasets[dataset].headers or {})}

    @property
    def schema(self) -> str:
        """Esquema do raw desta fonte: `raw_<esfera>_<fonte>` (o poder fica no contrato e na pasta)."""
        return f"raw_{self.level}_{self.source}"


def _dataset(source: str, name: str, data: dict[str, Any]) -> Dataset:
    where = f"{source}.{name}"
    raw = bool(data.get("raw", True))
    for required in ("url", "load", "write", "columns") if raw else ("url", "load"):
        if required not in data:
            raise InvalidContract(f"{where}: falta '{required}'")
    if data["load"] not in LOADS:
        raise InvalidContract(f"{where}: load '{data['load']}' inválido ({sorted(LOADS)})")
    if data.get("partition", "year") not in PARTITIONS:
        raise InvalidContract(f"{where}: partition '{data['partition']}' inválido ({sorted(PARTITIONS)})")
    if data.get("write", "replace") not in WRITES:
        raise InvalidContract(f"{where}: write '{data['write']}' inválido ({sorted(WRITES)})")
    if data.get("first_month") and data.get("partition") != "month":
        raise InvalidContract(f"{where}: first_month exige partition: month")
    if data.get("archive") is not None and data["archive"] not in ARCHIVES:
        raise InvalidContract(f"{where}: archive deve ser um de {sorted(ARCHIVES)}")
    if int(data.get("step", 1)) > 1 and data.get("first_year") is None:
        raise InvalidContract(f"{where}: step exige first_year")
    if data.get("format", "csv") not in FORMATS:
        raise InvalidContract(f"{where}: format deve ser um de {sorted(FORMATS)}")
    columns = tuple(data.get("columns", ()))
    for column in columns:
        if column.lower().replace("_", "") in FORBIDDEN_COLUMNS:
            raise InvalidContract(f"{where}: '{column}' é documento pessoal e nunca é lido")
    key = tuple(data.get("primary_key", ()))
    unknown = [new for new in data.get("aliases", {}).values() if new not in columns]
    if unknown:
        raise InvalidContract(f"{where}: aliases aponta para {unknown}, que não está em columns")
    absent = [c for c in data.get("optional", ()) if c not in columns]
    if absent:
        raise InvalidContract(f"{where}: optional {absent} não está em columns")
    stray = [c for c in data.get("nested", ()) if c not in columns]
    if stray:
        raise InvalidContract(f"{where}: nested {stray} não está em columns")
    foreach = _foreach(where, data) if data["load"] == "foreach" else None
    missing = [c for c in key if c not in columns and c != ROW_HASH]
    if missing:
        raise InvalidContract(f"{where}: chave {missing} não está em columns")
    if data.get("write") == "merge" and not key:
        raise InvalidContract(f"{where}: write merge exige primary_key")
    return Dataset(
        name=name,
        url=data["url"],
        load=data["load"],
        write=data.get("write", "replace"),
        columns=columns,
        primary_key=key,
        extra_years=bool(data.get("extra_years", False)),
        partition=str(data.get("partition", "year")),
        records=data.get("records"),
        nested=tuple(data.get("nested", ())),
        format=data.get("format"),
        headers=data.get("headers"),
        foreach=foreach,
        archive=data.get("archive"),
        member=str(data.get("member", "*")),
        raw=raw,
        arquivos=_arquivos(where, data),
        first_month=int(data["first_month"]) if data.get("first_month") else None,
        step=int(data.get("step", 1)),
        only={k: tuple(v) for k, v in data.get("only", {}).items()},
        aliases=dict(data.get("aliases", {})),
        optional=tuple(data.get("optional", ())),
        first_year=int(data["first_year"]) if data.get("first_year") is not None else None,
        max_age_days=_max_age(where, data.get("max_age_days")),
    )


def _arquivos(where: str, data: dict[str, Any]) -> Arquivos | None:
    block = data.get("arquivos")
    if block is None:
        return None
    unknown = set(block) - {"colecao", "caminho", "membro", "publicar"}
    if unknown or not {"colecao", "caminho"} <= set(block):
        raise InvalidContract(f"{where}: arquivos exige colecao e caminho e aceita só membro e publicar")
    if not re.fullmatch(r"[a-z][a-z0-9]*", str(block["colecao"])):
        raise InvalidContract(f"{where}: arquivos.colecao deve ser minúscula, sem separadores")
    if not isinstance(block.get("publicar", False), bool):
        raise InvalidContract(f"{where}: arquivos.publicar deve ser true ou false")
    fields = {"dataset", "particao", "nome"}
    if block.get("membro"):
        if data.get("archive") != "zip":
            raise InvalidContract(f"{where}: arquivos.membro exige archive: zip")
        try:
            fields |= set(re.compile(block["membro"]).groupindex)
        except re.error as error:
            raise InvalidContract(f"{where}: arquivos.membro inválido ({error})") from error
    used = {name for _, name, _, _ in string.Formatter().parse(block["caminho"]) if name}
    if used - fields or ".." in block["caminho"] or block["caminho"].startswith("/"):
        raise InvalidContract(
            f"{where}: arquivos.caminho usa campo desconhecido {sorted(used - fields)} ou sobe pastas"
        )
    return Arquivos(
        colecao=block["colecao"],
        caminho=block["caminho"],
        membro=block.get("membro"),
        publicar=block.get("publicar", False),
    )


def _max_age(where: str, value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise InvalidContract(f"{where}: max_age_days deve ser um número inteiro de dias, maior que zero")
    return value


def _foreach(where: str, data: dict[str, Any]) -> ForEach:
    spec = data.get("foreach")
    if not spec or "from" not in spec or "item" not in spec:
        raise InvalidContract(f"{where}: load foreach exige foreach.from e foreach.item")
    for name in ("item", "recent_by", "version"):
        if spec.get(name) and not IDENTIFIER.match(spec[name]):
            raise InvalidContract(f"{where}: foreach.{name} deve ser o nome de uma coluna")
    if "{item}" not in data["url"] or ITEM not in data["columns"] or ITEM not in data.get("primary_key", ()):
        raise InvalidContract(f"{where}: foreach exige {{item}} na url e {ITEM} em columns e primary_key")
    return ForEach(
        source=spec["from"],
        item=spec["item"],
        where=spec.get("where", "true"),
        recent_by=spec.get("recent_by"),
        version=spec.get("version"),
        refresh_after_days=spec.get("refresh_after_days"),
        batch_size=int(spec.get("batch_size", 500)),
    )


def _custom(power: str, level: str, source: str) -> ModuleType | None:
    """O módulo de código próprio da fonte (`ingestion/custom/<poder>/<esfera>/<fonte>.py`), se existir."""
    name = f"dado_publico_brasil.ingestion.custom.{power}.{level}.{source}"
    try:
        return importlib.import_module(name)
    except ModuleNotFoundError as error:
        if error.name and name.startswith(error.name):
            return None
        raise


def _rate_limit(value: Any, where: str) -> float:
    if float(value) <= 0:
        raise InvalidContract(f"{where}: access.rate_limit deve ser maior que zero")
    return float(value)


def load_contract(path: Path) -> SourceContract:
    """Lê e valida o contrato de uma fonte."""
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    access = data.get("access", {})
    source = data["source"]
    if access.get("format", "csv") not in FORMATS:
        raise InvalidContract(f"{source}: format deve ser um de {sorted(FORMATS)}")
    for field_name, allowed in (("power", POWERS), ("level", LEVELS)):
        if data.get(field_name) not in allowed:
            raise InvalidContract(f"{source}: {field_name} deve ser um de {sorted(allowed)}")
    schedule = data.get("schedule")
    if schedule is not None and (not isinstance(schedule, str) or len(schedule.split()) != 5):
        raise InvalidContract(
            f"{source}: schedule deve ser um cron de 5 campos (ex.: '0 6 * * *'), não {schedule!r}"
        )
    datasets = {n: _dataset(source, n, d) for n, d in data["datasets"].items()}
    for name, dataset in datasets.items():
        if dataset.foreach and dataset.foreach.source not in datasets:
            raise InvalidContract(
                f"{source}.{name}: foreach.from '{dataset.foreach.source}' não é um dataset"
            )
    custom = _custom(data["power"], data["level"], source)
    html = [n for n, d in datasets.items() if (d.format or access.get("format", "csv")) == "html"]
    if html and not hasattr(custom, "records"):
        raise InvalidContract(
            f"{source}: {html} é html e não tem leitor padrão: defina `records` no módulo próprio"
        )
    return SourceContract(
        source=source,
        power=data["power"],
        level=data["level"],
        description=data.get("description", source),
        base_url=access["base_url"],
        delimiter=access.get("delimiter", ";"),
        encoding=access.get("encoding", "utf-8-sig"),
        format=access.get("format", "csv"),
        rate_limit=_rate_limit(access.get("rate_limit", 4), source),
        schedule=schedule,
        headers=dict(access.get("headers", {})),
        custom=custom,
        datasets=datasets,
    )


def find(source: str) -> SourceContract:
    """Declaração de uma fonte, procurada em `sources/<poder>/<esfera>/<fonte>.yml`."""
    for path in SOURCES_DIR.glob(f"*/*/{source}.yml"):
        return load_contract(path)
    raise InvalidContract(f"fonte '{source}' não tem contrato em {SOURCES_DIR}")


def find_all() -> list[SourceContract]:
    """Todas as fontes declaradas em `sources/`."""
    return [load_contract(path) for path in sorted(SOURCES_DIR.glob("*/*/*.yml"))]
