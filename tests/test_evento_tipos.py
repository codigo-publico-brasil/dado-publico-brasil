"""O catálogo de tipos de evento aponta para tabelas que existem nos marts (ADR 0030, issue 186)."""

import csv
from pathlib import Path

DBT = Path(__file__).resolve().parents[1] / "dbt"


def test_fato_origem_is_a_mart_table() -> None:
    marts = {p.stem for p in (DBT / "models" / "marts").rglob("*.sql")}
    with (DBT / "seeds" / "marts" / "dim_evento_tipos.csv").open(encoding="utf-8") as f:
        origens = {r["id_tipo_evento"]: r["fato_origem"] for r in csv.DictReader(f)}
    # vazio é permitido: o tipo ainda não tem fonte aberta
    errados = {t: o for t, o in origens.items() if o and o not in marts}
    assert not errados
