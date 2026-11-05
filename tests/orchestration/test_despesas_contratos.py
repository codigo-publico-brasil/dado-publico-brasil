"""Despesas e contratos do Portal da Transparência: pacote mensal; CPF do contratado só no raw (privado), mascarado no staging."""

from dado_publico_brasil.core.settings import Settings
from dado_publico_brasil.core.warehouse import Connection, columns, scalar
from dado_publico_brasil.ingestion import contract as contracts

Env = tuple[Connection, Settings]
MENSAIS = ("despesas", "compras", "compras_itens", "compras_termos_aditivos")


def test_the_contract_is_polite_direct_and_covers_four_years() -> None:
    contrato = contracts.find("transparencia")
    assert contrato.rate_limit == 0.03  # uma requisição a cada ~33 segundos (ADR 0038)
    for nome in MENSAIS:
        dataset = contrato.datasets[nome]
        assert (dataset.partition, dataset.first_month) == ("month", 202211)
        assert contrato.url(nome, 202401).startswith("https://dadosabertos-download.cgu.gov.br/")
        assert "{" not in contrato.url(nome, 202401)


def test_expenses_and_contracts_reach_the_raw(full: Env) -> None:
    con, _ = full
    # cada mês é uma captura e uma partição (`replace_partition`): o pacote sintético é o mesmo nos 12 meses de 2024
    for table, rows_per_month in (
        ("despesas", 1),
        ("compras", 3),
        ("compras_itens", 2),
        ("compras_termos_aditivos", 2),
    ):
        per_capture = con.execute(
            f"SELECT count(*) FROM raw_federal_transparencia.{table} GROUP BY _source_file_id"
        ).fetchall()
        assert len(per_capture) == 12 and {n for (n,) in per_capture} == {rows_per_month}
    assert {"c_digo_contratado", "nome_contratado"} <= set(
        columns(con, "raw_federal_transparencia", "compras")
    )


def test_staging_converts_types_and_masks_the_cpf_in_free_text(full: Env) -> None:
    con, _ = full
    despesa = con.execute(
        "SELECT dt_lancamento, valor_empenhado FROM staging.stg_transparencia__despesas"
    ).fetchone()
    assert despesa
    dt, empenhado = despesa
    assert (str(dt), float(empenhado)) == ("2024-01-01", 805942.86)
    contrato = con.execute(
        "SELECT objeto, dt_assinatura, valor_inicial FROM staging.stg_transparencia__compras "
        "WHERE numero_contrato = '000012024'"
    ).fetchone()
    assert contrato
    objeto, assinatura, valor = contrato
    assert "123.456.789-09" not in objeto and "***.456.789-**" in objeto
    assert (str(assinatura), float(valor)) == ("2024-01-24", 205690.0)
    quantidades = con.execute(
        "SELECT DISTINCT quantidade FROM staging.stg_transparencia__compras_itens ORDER BY quantidade"
    ).fetchall()
    assert [float(q[0]) for q in quantidades] == [1.0, 1.5]  # a vírgula decimal vira ponto, com 4 casas
    for modelo in MENSAIS:
        assert (
            scalar(con, f"SELECT COUNT(*) FROM staging.stg_transparencia__{modelo} WHERE id_captura IS NULL")
            == 0
        )


def test_the_contractor_cpf_is_masked_in_staging_and_never_leaves_it_whole(full: Env) -> None:
    con, _ = full
    found = dict(
        con.execute("SELECT contratado, cd_contratado FROM staging.stg_transparencia__compras").fetchall()
    )
    assert found == {
        "EMPRESA EXEMPLO LTDA": "12345678000199",
        "PESSOA EXEMPLO": "***.456.789-**",
        "Sigiloso": "-11",  # marcadores da fonte para contrato sigiloso ficam como vêm
    }
    cpf = "[0-9]{3}[.]?[0-9]{3}[.]?[0-9]{3}-?[0-9]{2}"
    assert (
        scalar(
            con,
            "SELECT COUNT(*) FROM staging.stg_transparencia__compras "
            f"WHERE regexp_matches(cd_contratado || ' ' || contratado || ' ' || objeto, '(^|[^0-9]){cpf}($|[^0-9])')",
        )
        == 0
    )


def test_cpf_in_free_text_of_items_and_amendments_is_masked(full: Env) -> None:
    con, _ = full
    cpf = "[0-9]{3}[.]?[0-9]{3}[.]?[0-9]{3}-?[0-9]{2}"
    for table, columns_ in (
        ("compras_itens", "item || ' ' || item_descricao"),
        ("compras_termos_aditivos", "objeto"),
    ):
        assert (
            scalar(
                con,
                f"SELECT COUNT(*) FROM staging.stg_transparencia__{table} "
                f"WHERE regexp_matches({columns_}, '(^|[^0-9]){cpf}($|[^0-9])')",
            )
            == 0
        )
    assert "***.654.321-**" in scalar(
        con, "SELECT item_descricao FROM staging.stg_transparencia__compras_itens WHERE cd_item LIKE '%0002'"
    )
