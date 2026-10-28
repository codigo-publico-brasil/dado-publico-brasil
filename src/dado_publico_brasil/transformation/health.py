"""Saúde dos dados por dimensão de qualidade (issue 47): uma nota por dimensão e uma geral.

Cada teste do dbt cai em uma de seis dimensões (as mesmas do Elementary Cloud, para a classificação
não se perder se um dia houver migração). A classificação sai do nome do teste (not_null, unique,
relationships...) e, nos testes singulares, da pasta (`gaps` e `reconciliation`): um teste novo já
entra sozinho. O que não casar com nenhuma regra aparece como "sem dimensão", e um teste reprova.

Nota por teste: passou = 100, avisou = 50, falhou = 0. A nota da dimensão é a média; a geral é a
média das dimensões que têm teste. É nota de saúde dos DADOS, nunca de pessoas. Os testes de lacuna
(`gaps`) são avisos permanentes e puxam a completude para baixo de forma estável: por isso a lista do
que puxa vem junto com a nota.
"""

import re
from collections import defaultdict
from pathlib import Path

from dado_publico_brasil.core.settings import DBT_DIR
from dado_publico_brasil.core.warehouse import Connection

DIMENSIONS = {
    "freshness": "frescor",
    "completeness": "completude",
    "accuracy": "acurácia",
    "consistency": "consistência",
    "uniqueness": "unicidade",
    "validity": "validade",
}
# Por prefixo do nome do teste genérico (a primeira regra que casar vale).
RULES = (
    (r"elementary_freshness", "freshness"),
    (r"elementary_volume|elementary_all_columns|not_null_", "completeness"),
    (r"elementary_schema_changes|relationships_|dbt_utils_equal_rowcount", "consistency"),
    (r"unique_|dbt_utils_unique", "uniqueness"),
    (r"accepted_values_", "validity"),
)
SINGULAR = {"gaps": "completeness", "reconciliation": "consistency"}  # pasta em dbt/tests -> dimensão
SCORE = {"pass": 100, "warn": 50}  # qualquer outro estado (fail, error) vale 0
LATEST = (
    "SELECT unique_id, status, failures FROM metadata.dbt_results WHERE kind = 'test' AND run_id IN "
    "(SELECT max(id) FROM metadata.runs WHERE source = 'dbt' AND stage LIKE 'transform%' GROUP BY stage)"
)


def singular_tests(folder: Path = DBT_DIR / "tests") -> dict[str, str]:
    """Nome de cada teste singular -> dimensão da pasta em que está."""
    return {
        file.stem: dimension
        for directory, dimension in SINGULAR.items()
        for file in (folder / directory).glob("*.sql")
    }


def dimension_of(unique_id: str, singular: dict[str, str]) -> str | None:
    """A dimensão de um teste pelo `unique_id` do dbt (`test.<projeto>.<nome>[.<hash>]`), ou None."""
    parts = unique_id.split(".")
    name = parts[2] if len(parts) > 2 else unique_id
    if name in singular:
        return singular[name]
    name = name.removeprefix("source_")  # os testes declarados nas fontes do raw têm o mesmo tipo
    for pattern, dimension in RULES:
        if re.match(pattern, name):
            return dimension
    return None


def short(unique_id: str) -> str:
    parts = unique_id.split(".")
    return parts[2] if len(parts) > 2 else unique_id


def lines(con: Connection) -> list[str]:
    """A seção "Saúde por dimensão" do relatório, dos resultados de teste do último build de cada fase."""
    results = con.execute(LATEST).fetchall()
    if not results:
        return ["Saúde por dimensão: sem resultados de teste"]
    singular = singular_tests()
    scores: dict[str, list[int]] = defaultdict(list)
    pulling: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for unique_id, status, _ in results:
        dimension = dimension_of(str(unique_id), singular) or "sem dimensão"
        scores[dimension].append(SCORE.get(str(status), 0))
        if status != "pass":
            pulling[dimension].append((str(status), short(str(unique_id))))
    rated = {d: sum(v) / len(v) for d, v in scores.items() if d in DIMENSIONS}
    overall = sum(rated.values()) / len(rated) if rated else 0
    out = [
        f"Saúde por dimensão (testes do último build; passou 100, avisou 50, falhou 0): geral {overall:.0f}"
    ]
    for key, label in DIMENSIONS.items():
        values = scores.get(key)
        if not values:
            out.append(f"  {label}: sem testes")
            continue
        warns = sum(1 for s, _ in pulling[key] if s == "warn")
        fails = len(pulling[key]) - warns
        out.append(f"  {label}: {rated[key]:.0f} ({len(values)} testes, {warns} avisos, {fails} falhas)")
        out += [f"    puxa para baixo: [{s}] {name}" for s, name in sorted(pulling[key])[:3]]
        if len(pulling[key]) > 3:
            out.append(f"    ... e mais {len(pulling[key]) - 3}")
    if "sem dimensão" in scores:
        out.append(
            f"  sem dimensão: {len(scores['sem dimensão'])} testes (classifique em transformation/health.py)"
        )
    return out
