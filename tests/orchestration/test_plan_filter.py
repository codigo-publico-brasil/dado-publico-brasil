"""`--dataset` limita a extração a um dataset: os pesados (votos do TSE) vão por ano, sem baixar os outros."""

import argparse

from dado_publico_brasil.ingestion import contract
from dado_publico_brasil.orchestration.__main__ import _plan


def args(**kw: object) -> argparse.Namespace:
    base = {"incremental": False, "historical": False, "years": [2022], "extra_years": [], "dataset": None}
    return argparse.Namespace(**{**base, **kw})


def test_without_dataset_the_plan_has_every_yearly_dataset_of_the_source() -> None:
    items = _plan(args())(contract.find("tse"))
    names = {name for name, _ in items}
    assert {
        "candidaturas",
        "bens",
        "votacao",
        "vagas",
        "receitas_candidatos",
        "despesas_candidatos",
    } <= names
    assert len({n for n in names if n.startswith("fotos_")}) == 28  # o Brasil e as 27 UFs


def test_with_dataset_only_that_one_is_planned() -> None:
    assert _plan(args(dataset="bens"))(contract.find("tse")) == [("bens", 2022)]
    assert _plan(args(dataset="bens", years=[2006, 2010, 2022]))(contract.find("tse")) == [
        ("bens", 2006),
        ("bens", 2010),
        ("bens", 2022),
    ]
