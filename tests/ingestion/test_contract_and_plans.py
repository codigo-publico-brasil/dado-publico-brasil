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


def test_incremental_plan_has_only_the_current_partition_of_each_dataset_that_refreshes_daily(
    contract: SourceContract,
) -> None:
    items = landing.plan_incremental(contract, today=date(2026, 10, 24))
    assert [y for d, y in items if d == "proposicoes"] == [2026]  # nada retroativo: só o ano em curso
    assert ("deputados", None) in items
    assert ("votacoes", 2025) not in items


def test_each_source_declares_how_it_refreshes_and_what_is_on_request_stays_out_of_the_daily_plan() -> None:
    today = date(2026, 10, 24)
    assert landing.plan_incremental(contracts.find("tse"), today) == []  # TSE: pontual, só quando pedido
    assert {name for name, _ in landing.plan_incremental(contracts.find("dou"), today)} == {
        "secao1",
        "secao2",
        "secao3",
    }
    assert {part for _, part in landing.plan_incremental(contracts.find("dou"), today)} == {
        202610
    }  # só o mês em curso
    senate = dict(landing.plan_incremental(contracts.find("senado"), today))
    assert senate["senadores"] == landing.legislature_of(2026) and senate["votacoes"] == 2026


def test_an_invalid_refresh_is_refused(tmp_path: Path) -> None:
    file = tmp_path / "fonte.yml"
    lines = [
        "source: x",
        "power: legislativo",
        "level: federal",
        "access: {base_url: 'http://x'}",
        "datasets:",
        "  d: {url: 'http://x/d.csv', load: full, write: replace, columns: [a], refresh: semanal}",
    ]
    file.write_text(chr(10).join(lines), encoding="utf-8")
    with pytest.raises(InvalidContract, match="refresh"):
        load_contract(file)


def test_unchanged_uses_etag_or_last_modified_with_size() -> None:
    previous = {"etag": '"a"', "last_modified": "ontem", "size_bytes": 10}
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


def test_legislature_partition_maps_years_to_legislatures_and_builds_the_url(
    contract: SourceContract,
) -> None:
    assert [landing.legislature_of(y) for y in (2000, 2002, 2003, 2018, 2019, 2022, 2023, 2026, 2027)] == [
        51,
        51,
        52,
        55,
        56,
        56,
        57,
        57,
        58,
    ]
    assert contract.url("orgaosDeputados", 57).endswith("/orgaosDeputados/csv/orgaosDeputados-L57.csv")
    items = landing.plan_historical(contract, 2000, 2026)
    assert [v for n, v in items if n == "orgaosDeputados"] == [51, 52, 53, 54, 55, 56, 57]
    assert [v for n, v in landing.plan(contract, [2024]) if n == "orgaosDeputados"] == [57]


def test_contract_without_a_valid_power_or_level_is_refused(tmp_path: Path) -> None:
    for field, value in (("power", "militar"), ("level", "regional")):
        text = TEMPLATE.format(extra="").replace(f"{field}: ", f"{field}: {value} #")
        with pytest.raises(InvalidContract, match=field):
            contract_from(tmp_path, text=text)


def test_raw_schema_carries_the_level_and_the_source(tmp_path: Path) -> None:
    assert contract_from(tmp_path).schema == "raw_municipal_teste"
