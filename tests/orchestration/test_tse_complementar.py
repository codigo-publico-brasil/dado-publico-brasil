"""TSE complementar: bens declarados e votos por candidato (todos os cargos no raw; marts só de quem é pessoa)."""

from dado_publico_brasil.core.settings import Settings
from dado_publico_brasil.core.warehouse import Connection, columns, scalar

Env = tuple[Connection, Settings]


def test_raw_keeps_assets_and_votes_of_every_office_and_never_the_social_name(full: Env) -> None:
    con, _ = full
    assert scalar(con, "SELECT COUNT(*) FROM raw_federal_tse.bens") == 4  # inclui o deputado estadual
    assert scalar(con, "SELECT COUNT(*) FROM raw_federal_tse.votacao") == 6  # o `_SP.csv` de ruído não é lido
    assert "nm_social_candidato" not in columns(con, "raw_federal_tse", "votacao")
    assert scalar(con, "SELECT COUNT(DISTINCT ds_cargo) FROM raw_federal_tse.votacao") == 2


def test_assets_are_exposed_only_for_candidates_who_are_people_with_the_declared_value(full: Env) -> None:
    con, _ = full
    found = con.execute(
        "SELECT p.nome, b.id_candidatura, b.ordem, b.tipo, b.valor FROM marts.fct_candidaturas_bens b "
        "JOIN marts.dim_pessoas_cadastro p USING (id_pessoa) ORDER BY b.id_candidatura, b.ordem"
    ).fetchall()
    assert [(f[0], f[1], f[2], f[3], float(f[4])) for f in found] == [
        ("Bia", "2022:RJ:1001", 1, "Casa", 150000.0),
        ("Bia", "2022:RJ:1001", 2, "Veículo automotor terrestre", 30000.5),
        ("Ana Árvore", "2022:SP:1002", 1, "Aplicação de renda fixa", 5000.0),
    ]  # o terreno do candidato estadual (1006) fica só no staging
    assert scalar(con, "SELECT COUNT(*) FROM staging.stg_tse__bens") == 4


def test_votes_are_summed_per_candidacy_and_the_annulled_ones_stay_out_of_the_valid_total(full: Env) -> None:
    con, _ = full
    found = con.execute(
        "SELECT p.nome, v.cargo, v.uf, v.votos_nominais, v.votos_validos, v.municipios "
        "FROM marts.fct_candidaturas_votos v JOIN marts.dim_pessoas_cadastro p USING (id_pessoa) ORDER BY v.id_candidatura"
    ).fetchall()
    assert found == [
        ("Bia", "Deputado federal", "RJ", 1770, 1750, 2),
        ("Ana Árvore", "Deputado federal", "SP", 700, 700, 1),
    ]
    assert (
        scalar(con, "SELECT COUNT(*) FROM staging.stg_tse__votacao") == 6
    )  # os votos por município ficam no staging


def test_the_votes_total_reconciles_between_staging_and_marts(full: Env) -> None:
    con, _ = full
    for name in ("bens_perdidos_do_staging_aos_marts", "votos_de_candidatos_perdidos_do_staging_aos_marts"):
        assert scalar(con, f"SELECT failures FROM metadata.dbt_results WHERE unique_id LIKE '%{name}%'") == 0
