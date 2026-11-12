"""Cota parlamentar (CEAP da Câmara e CEAPS do Senado): leitura dos dois formatos, CPF mascarado, ligação à pessoa."""

from dado_publico_brasil.core.settings import Settings
from dado_publico_brasil.core.warehouse import Connection, scalar

Env = tuple[Connection, Settings]


def test_both_houses_enter_with_one_row_per_expense(full: Env) -> None:
    con, _ = full
    assert scalar(con, "SELECT COUNT(*) FROM raw_federal_camara.cota_parlamentar") == 4
    assert scalar(con, "SELECT COUNT(*) FROM raw_federal_senado.ceaps") == 3
    assert con.execute(
        "SELECT fonte, COUNT(*) FROM marts.fct_cotas_despesas GROUP BY 1 ORDER BY 1"
    ).fetchall() == [
        ("camara", 4),
        ("senado", 3),
    ]


def test_the_raw_keeps_only_the_allowed_columns(full: Env) -> None:
    con, _ = full
    columns = {r[0] for r in con.execute("DESCRIBE raw_federal_camara.cota_parlamentar").fetchall()}
    assert not columns & {"cpf", "tx_passageiro", "nu_carteira_parlamentar"}


def test_the_senate_file_is_read_in_latin1_after_the_notice_line(full: Env) -> None:
    con, _ = full
    found = con.execute(
        "SELECT tipo_despesa, fornecedor, valor_reembolsado, dt_emissao FROM marts.fct_cotas_despesas "
        "WHERE id_documento = '9001'"
    ).fetchone()
    assert found is not None
    assert found[:3] == ("Divulgação da atividade parlamentar", "GRÁFICA X LTDA", 1500.75)
    assert str(found[3]) == "2020-03-05"


def test_the_chamber_values_keep_sign_and_stay_apart_from_the_senate_value(full: Env) -> None:
    con, _ = full
    found = con.execute(
        "SELECT valor_documento, valor_glosa, valor_liquido, valor_reembolsado FROM marts.fct_cotas_despesas "
        "WHERE fonte = 'camara' AND id_documento = '5002'"
    ).fetchone()
    assert found is not None and (found[0], found[1], found[2], found[3]) == (80, 10, 70, None)
    assert (
        scalar(con, "SELECT valor_liquido FROM marts.fct_cotas_despesas WHERE id_documento = '5004'") == -20
    )


def test_the_supplier_cpf_is_masked_everywhere_it_appears(full: Env) -> None:
    con, _ = full
    assert scalar(con, "SELECT COUNT(*) FROM marts.fct_cotas_despesas WHERE fl_fornecedor_pessoa_fisica") == 2
    leaked = scalar(
        con,
        "SELECT COUNT(*) FROM marts.fct_cotas_despesas WHERE documento_fornecedor LIKE '%123.456.789-09%' "
        "OR detalhamento LIKE '%123.456.789-09%'",
    )
    assert leaked == 0
    assert (
        scalar(con, "SELECT documento_fornecedor FROM marts.fct_cotas_despesas WHERE id_documento = '5002'")
        == "***.456.789-**"
    )
    assert (
        scalar(con, "SELECT detalhamento FROM marts.fct_cotas_despesas WHERE id_documento = '9002'")
        == "Serviço do CPF ***.456.789-**"
    )


def test_a_deputy_is_linked_by_the_id_the_source_publishes(full: Env) -> None:
    con, _ = full
    ana = scalar(con, "SELECT id_pessoa FROM marts.dim_pessoas WHERE nome_civil = 'Ana da Silva'")
    assert (
        con.execute(
            "SELECT id_pessoa, regra_ligacao_pessoa, precisao_ligacao_pessoa FROM marts.fct_cotas_despesas "
            "WHERE fonte = 'camara' AND id_documento IN ('5001', '5002')"
        ).fetchall()
        == [(ana, "id_na_fonte", "informada")] * 2
    )


def test_a_senator_is_linked_by_name_and_exercise_and_marked_as_derived(full: Env) -> None:
    con, _ = full
    found = con.execute(
        "SELECT id_pessoa IS NOT NULL, regra_ligacao_pessoa, precisao_ligacao_pessoa "
        "FROM marts.fct_cotas_despesas WHERE id_documento = '9001'"
    ).fetchone()
    assert found == (True, "nome_parlamentar_e_exercicio", "derivada")


def test_what_does_not_match_stays_without_person_rule_and_precision(full: Env) -> None:
    con, _ = full
    assert con.execute(
        "SELECT id_documento, id_pessoa, regra_ligacao_pessoa, precisao_ligacao_pessoa FROM marts.fct_cotas_despesas "
        "WHERE id_documento IN ('5003', '5004', '9003') ORDER BY 1"
    ).fetchall() == [("5003", None, None, None), ("5004", None, None, None), ("9003", None, None, None)]


def test_the_unlinked_expenses_are_measured_as_a_gap_but_not_the_leadership_row(full: Env) -> None:
    con, _ = full
    # o deputado fora do cadastro e o senador sem correspondência; a linha de liderança (UF "NA") não conta
    assert (
        scalar(
            con,
            "SELECT qtd_falhas FROM metadata.testes_resultados WHERE id_no LIKE '%cotas_despesas_sem_pessoa%'",
        )
        == 2
    )


def test_the_table_is_classified_and_its_personal_columns_are_marked(full: Env) -> None:
    from dado_publico_brasil.transformation import catalog

    settings = Settings()
    sensitivity = {t["name"]: t["sensitivity"] for t in catalog.tables(settings) if t["schema"] == "marts"}
    assert sensitivity["fct_cotas_despesas"] == "publico-dados-pessoais-de-terceiros"
    marked = {c["name"] for c in catalog.columns(settings) if c["table"] == "fct_cotas_despesas" and c["pii"]}
    assert marked == {"fornecedor", "documento_fornecedor", "detalhamento"}
