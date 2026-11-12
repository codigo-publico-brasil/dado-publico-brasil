"""Contrato da fonte (validação) e planos de extração (explícito, histórico e incremental)."""

from datetime import date
from pathlib import Path

import pytest

from dado_publico_brasil.ingestion import contract as contracts
from dado_publico_brasil.ingestion import landing
from dado_publico_brasil.ingestion.contract import InvalidContract, SourceContract, load_contract

TEMPLATE = """
source: teste
power: legislativo
level: municipal
description: Fonte de teste
access: {{base_url: "http://exemplo", delimiter: ",", encoding: utf-8}}
datasets:
  pessoas:
    url: "{{base_url}}/pessoas-{{year}}.csv"
    load: yearly
    write: merge
    primary_key: [codigo]
    columns: [codigo, nome{extra}]
"""


def contract_from(tmp_path: Path, extra: str = "", text: str | None = None) -> SourceContract:
    file = tmp_path / "contract.yml"
    file.write_text(text or TEMPLATE.format(extra=extra), encoding="utf-8")
    return load_contract(file)


def test_contract_builds_the_official_url_for_full_and_yearly_datasets(
    contract: SourceContract,
) -> None:
    assert contract.url("deputados").endswith("/deputados/csv/deputados.csv")
    assert contract.url("votacoes", 2024).endswith("/votacoes/csv/votacoes-2024.csv")
    with pytest.raises(ValueError, match="particionado"):
        contract.url("votacoes")


@pytest.mark.parametrize("column", ["cpf", "rg", "tituloEleitor", "titulo_eleitor"])
def test_contract_that_lists_a_personal_document_is_refused(tmp_path: Path, column: str) -> None:
    with pytest.raises(InvalidContract, match="documento pessoal"):
        contract_from(tmp_path, extra=f", {column}")


def test_contract_with_bad_key_load_or_write_is_refused(tmp_path: Path) -> None:
    with pytest.raises(InvalidContract, match="chave"):
        contract_from(tmp_path, text=TEMPLATE.format(extra="").replace("[codigo]", "[inexistente]"))
    with pytest.raises(InvalidContract, match="load"):
        contract_from(tmp_path, text=TEMPLATE.format(extra="").replace("yearly", "mensal"))
    with pytest.raises(InvalidContract, match="merge exige primary_key"):
        contract_from(tmp_path, text=TEMPLATE.format(extra="").replace("    primary_key: [codigo]\n", ""))


@pytest.mark.parametrize("value", ["0", "-3", "tres", "true", "2.5"])
def test_contract_with_a_bad_max_age_days_is_refused(tmp_path: Path, value: str) -> None:
    text = TEMPLATE.format(extra="") + f"    max_age_days: {value}" + chr(10)
    with pytest.raises(InvalidContract, match="max_age_days"):
        contract_from(tmp_path, text=text)


def test_contract_reads_max_age_days_and_every_real_source_still_loads(tmp_path: Path) -> None:
    text = TEMPLATE.format(extra="") + "    max_age_days: 3" + chr(10)
    assert contract_from(tmp_path, text=text).datasets["pessoas"].max_age_days == 3
    limits = [d.max_age_days for c in contracts.find_all() for d in c.datasets.values() if d.max_age_days]
    assert limits and all(days >= 1 for days in limits)


TOLERANCE = "    tolerated_rejects:\n      2004: {limit: 1, reason: linha da fonte sem chave}\n"


def test_contract_reads_the_tolerated_rejections_per_partition(tmp_path: Path) -> None:
    dataset = contract_from(tmp_path, text=TEMPLATE.format(extra="") + TOLERANCE).datasets["pessoas"]
    assert dataset.tolerated_rejects[2004].limit == 1
    assert dataset.tolerated_rejects[2004].reason == "linha da fonte sem chave"
    assert contract_from(tmp_path).datasets["pessoas"].tolerated_rejects == {}


@pytest.mark.parametrize(
    "block",
    [
        "{limit: 0, reason: x}",
        "{limit: 1}",
        "{limit: 1, reason: ''}",
        "{limit: um, reason: x}",
    ],
)
def test_contract_with_a_bad_tolerance_is_refused(tmp_path: Path, block: str) -> None:
    text = TEMPLATE.format(extra="") + f"    tolerated_rejects:\n      2004: {block}\n"
    with pytest.raises(InvalidContract, match="tolerated_rejects"):
        contract_from(tmp_path, text=text)


def test_explicit_plan_has_full_datasets_and_the_requested_years(contract: SourceContract) -> None:
    items = landing.plan(contract, [2025, 2024], [2019])
    assert ("deputados", None) in items
    assert ("proposicoes", 2019) in items
    assert ("votacoes", 2019) not in items
    assert ("votacoesVotos", 2024) in items


def test_historical_plan_covers_every_year_of_the_range(contract: SourceContract) -> None:
    items = landing.plan_historical(contract, 2023, 2026)
    assert ("proposicoes", 2023) in items
    assert ("votacoesVotos", 2026) in items


def test_incremental_plan_has_only_the_current_partition_of_each_dataset_of_a_scheduled_source(
    contract: SourceContract,
) -> None:
    items = landing.plan_incremental(contract, today=date(2026, 10, 24))
    assert [y for d, y in items if d == "proposicoes"] == [2026]  # nada retroativo: só o ano em curso
    assert ("deputados", None) in items
    assert ("votacoes", 2025) not in items


def test_a_source_without_schedule_has_an_empty_incremental_plan(tmp_path: Path) -> None:
    assert contract_from(tmp_path).schedule is None
    assert landing.plan_incremental(contract_from(tmp_path), date(2026, 10, 24)) == []  # só quando pedido


def test_each_source_declares_its_schedule_and_the_plan_has_only_the_current_partition() -> None:
    today = date(2026, 10, 24)
    # nenhuma fonte fica sem cadência por esquecimento; o TSE está desativado após as eleições (ADR 0042)
    assert {c.source for c in contracts.find_all() if not c.schedule} == {"tse"}
    assert landing.plan_incremental(contracts.find("tse"), today) == []  # sem schedule, só quando pedido
    assert {name for name, _ in landing.plan_incremental(contracts.find("dou"), today)} == {
        "secao1",
        "secao2",
        "secao3",
    }
    assert {part for _, part in landing.plan_incremental(contracts.find("dou"), today)} == {
        202609,
        202610,
    }  # o mês em curso e o anterior
    senate = dict(landing.plan_incremental(contracts.find("senado"), today))
    assert senate["senadores"] == 57 and senate["votacoes"] == 2026


def test_an_invalid_schedule_is_refused(tmp_path: Path) -> None:
    with pytest.raises(InvalidContract, match="schedule"):
        contract_from(tmp_path, text="schedule: toda segunda" + chr(10) + TEMPLATE.format(extra=""))
    assert contract_from(
        tmp_path, text="schedule: '0 6 * * *'" + chr(10) + TEMPLATE.format(extra="")
    ).schedule


def test_unchanged_uses_etag_or_last_modified_with_size() -> None:
    previous = {"etag": '"a"', "ultima_modificacao": "ontem", "qtd_bytes": 10}
    assert landing.unchanged(previous, {"etag": '"a"'})
    assert landing.unchanged(previous, {"last_modified": "ontem", "size": "10"})
    assert not landing.unchanged(previous, {"last_modified": "ontem", "size": "11"})
    assert not landing.unchanged(previous, {})
    assert not landing.unchanged(None, {"etag": '"a"'})


def test_historical_plan_skips_years_before_the_first_year_the_source_publishes(
    contract: SourceContract,
) -> None:
    items = landing.plan_historical(contract, 2000, 2004)
    assert ("votacoes", 2000) in items
    assert ("votacoesVotos", 2000) not in items
    assert ("votacoesVotos", 2001) in items
    assert ("votacoesOrientacoes", 2002) not in items
    assert ("votacoesOrientacoes", 2003) in items


def _old_legislature_of(year: int) -> int:
    """O cálculo que o núcleo fazia antes de a sequência ir para o YAML (só aqui, como prova)."""
    return 56 + (year - 2019) // 4


def test_sequence_partition_gives_the_same_partitions_urls_and_paths_as_the_old_legislature(
    contract: SourceContract,
) -> None:
    years = list(range(1990, 2041))
    for source, name in (("camara", "orgaosDeputados"), ("senado", "senadores")):
        c = contracts.find(source)
        d = c.datasets[name]
        assert d.partition == "sequence" and d.sequence == (2019, 56, 4)
        valid = [y for y in years if d.first_year is None or y >= d.first_year]
        assert landing.partitions(d, years) == sorted({_old_legislature_of(y) for y in valid})
        for y in range(1990, 2041):
            assert landing.current_partition(d, date(y, 6, 1)) == _old_legislature_of(y)
            v = _old_legislature_of(y)
            old_url = d.url.replace("{partition}", "{legislature}").format(base_url=c.base_url, legislature=v)
            assert c.url(name, v) == old_url
    assert contract.url("orgaosDeputados", 57).endswith("/orgaosDeputados/csv/orgaosDeputados-L57.csv")
    items = landing.plan_historical(contract, 2000, 2026)
    assert [v for n, v in items if n == "orgaosDeputados"] == [51, 52, 53, 54, 55, 56, 57]
    assert [v for n, v in landing.plan(contract, [2024]) if n == "orgaosDeputados"] == [57]


def test_sequence_partition_needs_its_declaration_and_legislature_is_refused(tmp_path: Path) -> None:
    base = TEMPLATE.format(extra="")
    bad_ones = (
        "partition: legislature",
        "partition: sequence",
        "partition: sequence" + chr(10) + "    sequence: {first_year: 2019}",
    )
    for bad in bad_ones:
        text = base.replace("load: yearly", "load: yearly" + chr(10) + "    " + bad)
        with pytest.raises(InvalidContract, match="partition|sequence"):
            contract_from(tmp_path, text=text)


def test_contract_without_a_valid_power_or_level_is_refused(tmp_path: Path) -> None:
    for field, value in (("power", "militar"), ("level", "regional")):
        text = TEMPLATE.format(extra="").replace(f"{field}: ", f"{field}: {value} #")
        with pytest.raises(InvalidContract, match=field):
            contract_from(tmp_path, text=text)


def test_raw_schema_carries_the_level_and_the_source(tmp_path: Path) -> None:
    assert contract_from(tmp_path).schema == "raw_municipal_teste"


@pytest.mark.parametrize(
    "block, message",
    [
        ("{collection: x}", "collection e path"),
        ("{collection: x, path: a, other: 1}", "collection e path"),
        ("{collection: Fotos_1, path: a}", "collection"),
        ("{collection: x, path: a, publish: sim}", "publish"),
        ("{collection: x, path: '{inexistente}'}", "campo desconhecido"),
        ("{collection: x, path: '../{name}'}", "sobe pastas"),
        ("{collection: x, path: '{name}', member: 'a'}", "archive: zip"),
    ],
)
def test_contract_with_a_bad_files_block_is_refused(tmp_path: Path, block: str, message: str) -> None:
    text = TEMPLATE.format(extra="") + f"    files: {block}" + chr(10)
    with pytest.raises(InvalidContract, match=message):
        contract_from(tmp_path, text=text)


def test_files_block_is_read_and_the_member_groups_become_path_fields(tmp_path: Path) -> None:
    block = "{collection: x, path: '{partition}/{uf}/{name}', member: '^(?P<uf>[A-Z]{2})', publish: true}"
    text = TEMPLATE.format(extra="") + f"    archive: zip\n    files: {block}" + chr(10)
    spec = contract_from(tmp_path, text=text).datasets["pessoas"].files
    assert spec is not None and spec.publish and spec.collection == "x"
    published = {
        (c.source, n): d.files.collection
        for c in contracts.find_all()
        for n, d in c.datasets.items()
        if d.files and d.files.publish
    }
    assert published[("dou", "secao1")] == "secoes" and published[("tse", "fotos_rj")] == "fotos"


def test_rate_limit_must_be_positive(tmp_path: Path) -> None:
    text = TEMPLATE.format(extra="").replace("encoding: utf-8}", "encoding: utf-8, rate_limit: 0}")
    with pytest.raises(InvalidContract, match="rate_limit"):
        contract_from(tmp_path, text=text)


def test_on_demand_must_be_a_boolean(tmp_path: Path) -> None:
    def text(value: str) -> str:
        return TEMPLATE.format(extra="") + f"    on_demand: {value}" + chr(10)

    with pytest.raises(InvalidContract, match="on_demand"):
        contract_from(tmp_path, text=text("sim"))
    assert contract_from(tmp_path, text=text("true")).datasets["pessoas"].on_demand
    assert not contract_from(tmp_path).datasets["pessoas"].on_demand


@pytest.mark.parametrize(
    ("old", "new", "typo", "where"),
    [
        ("schedule", "shedule", "shedule", "a fonte"),
        ("access:", "acess:", "acess", "a fonte"),
        ("primary_key:", "primay_key:", "primay_key", "dataset"),
        ("encoding: utf-8}", "encoding: utf-8, delimeter: ';'}", "delimeter", "access"),
    ],
)
def test_an_unknown_key_is_refused_naming_the_key_and_the_file(
    tmp_path: Path, old: str, new: str, typo: str, where: str
) -> None:
    text = TEMPLATE.format(extra="").replace(
        "level: municipal", "level: municipal" + chr(10) + "schedule: '0 6 * * *'"
    )
    with pytest.raises(InvalidContract, match=f"contract.yml.*{where}.*{typo}"):
        contract_from(tmp_path, text=text.replace(old, new, 1))


def test_an_unknown_foreach_key_is_refused(tmp_path: Path) -> None:
    text = TEMPLATE.format(extra="") + "    foreach: {from: a, item: b, wher: 'true'}" + chr(10)
    with pytest.raises(InvalidContract, match="wher"):
        contract_from(tmp_path, text=text)


def test_license_is_optional_text() -> None:
    assert contracts.find("tse").license == "CC BY"
    assert contracts.find("camara").license is None  # a doc de fontes não registra licença formal
