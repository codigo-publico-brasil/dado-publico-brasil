"""Funções de padronização de texto (macros nativas do DuckDB em `dbt/macros`)."""

from pathlib import Path

import duckdb
import pytest

MACROS = Path(__file__).resolve().parents[2] / "dbt" / "macros" / "text_functions.sql"


@pytest.fixture(scope="module")
def db() -> duckdb.DuckDBPyConnection:
    body = MACROS.read_text(encoding="utf-8").split("{% macro create_text_functions() %}")[1]
    connection = duckdb.connect()
    connection.execute(body.split("{% endmacro %}")[0])
    return connection


def one(db: duckdb.DuckDBPyConnection, sql: str, *args: object) -> object:
    row = db.execute(sql, list(args)).fetchone()
    assert row is not None
    return row[0]


@pytest.mark.parametrize(
    ("original", "expected"),
    [
        ("MARIA APARECIDA DA SILVA SOUZA", "Maria Aparecida da Silva Souza"),
        ("PEREIRA DA COSTA", "Pereira da Costa"),
        ("maria dos santos", "Maria dos Santos"),
        ("Maria Souza", "Maria Souza"),
        ("João da Silva Neto", "João da Silva Neto"),
        ("XYZ", "XYZ"),
        ("PEDRO II", "Pedro II"),
        ("D'ÁVILA E SILVA", "D'Ávila e Silva"),
        ("ANA-MARIA LIMA", "Ana-Maria Lima"),
        ("  JOAO   ROMA ", "Joao Roma"),
    ],
)
def test_proper_name_only_changes_single_case_text(
    db: duckdb.DuckDBPyConnection, original: str, expected: str
) -> None:
    assert one(db, "SELECT proper_name(?)", original) == expected


def test_proper_name_of_empty_or_null_is_null(db: duckdb.DuckDBPyConnection) -> None:
    assert one(db, "SELECT proper_name(NULL)") is None
    assert one(db, "SELECT proper_name('   ')") is None


def test_sentence_case(db: duckdb.DuckDBPyConnection) -> None:
    assert one(db, "SELECT sentence_case(?)", "COMISSÃO PERMANENTE") == "Comissão permanente"
    assert one(db, "SELECT sentence_case(?)", "Órgão do Poder Executivo") == "Órgão do Poder Executivo"


def test_standardize_summary_keeps_known_acronyms_and_sentence_starts(
    db: duckdb.DuckDBPyConnection,
) -> None:
    text = "REQUER AO BNDES INFORMAÇÕES. DISPÕE SOBRE O ASSUNTO"
    result = one(db, "SELECT standardize_summary(?, ['BNDES'])", text)
    assert result == "Requer ao BNDES informações. Dispõe sobre o assunto"


def test_standardize_summary_leaves_mixed_case_alone_and_capitalizes_lowercase(
    db: duckdb.DuckDBPyConnection,
) -> None:
    mixed = "Altera a Lei nº 11.340, de 2006."
    assert one(db, "SELECT standardize_summary(?, []::varchar[])", mixed) == mixed
    lower = "requer o desarquivamento de proposições."
    assert one(db, "SELECT standardize_summary(?, []::varchar[])", lower) == (
        "Requer o desarquivamento de proposições."
    )


def test_name_key_compares_names_across_sources(db: duckdb.DuckDBPyConnection) -> None:
    assert one(db, "SELECT name_key(?)", "  José   da  SILVA ") == "jose da silva"
    assert one(db, "SELECT name_key(?)", "Jose da Silva") == one(db, "SELECT name_key(?)", "JOSÉ DA SILVA")
    assert one(db, "SELECT name_key(NULL)") is None
    assert one(db, "SELECT name_key('   ')") is None


@pytest.mark.parametrize(
    ("original", "expected"),
    [
        ("VEICULO DA ESPOSA, CPF/MF: 999.999.999-99", "VEICULO DA ESPOSA, CPF/MF: ***.999.999-**"),
        ("IMOVEL cpf 99999999999 DO PAI", "IMOVEL cpf ***.999.999-** DO PAI"),
        ("RENAVAM 12345678901 PLACA ABC", "RENAVAM 12345678901 PLACA ABC"),
        ("DEPOSITO AG. 1234 C/C 56789-0", "DEPOSITO AG. 1234 C/C 56789-0"),
        ("Agência 1234, conta corrente nº 56789-X", "Agência 1234, conta corrente nº 56789-X"),
        ("CASA COM 3 QUARTOS", "CASA COM 3 QUARTOS"),
        ("TERRENO DE PESSOA EXEMPLO 999.999.999-99 EM SP", "TERRENO DE PESSOA EXEMPLO ***.999.999-** EM SP"),
        ("PROCESSO 1234.567.890-12 E 12.345.678/0001-99", "PROCESSO 1234.567.890-12 E 12.345.678/0001-99"),
        # agência e conta bancária vêm como a fonte publica (ADR 0050): a descrição não é alterada
        ("MOTO 150 CC ANO 2019 E CONTA 3 PARCELAS", "MOTO 150 CC ANO 2019 E CONTA 3 PARCELAS"),
        ("conta de luz paga em 2019", "conta de luz paga em 2019"),
        ("AG 123 DO BANCO", "AG 123 DO BANCO"),
        ("CONTA CORRENTE N. 12345-6", "CONTA CORRENTE N. 12345-6"),
        ("AGENCIA 1234 CONTA 12.345-X", "AGENCIA 1234 CONTA 12.345-X"),
        ("SALDO C/C12345-6 E CONTA99999", "SALDO C/C12345-6 E CONTA99999"),
        ("CONTA 99-123456-7, SALDO", "CONTA 99-123456-7, SALDO"),
        ("CONTA 1234-56789-0 FIM", "CONTA 1234-56789-0 FIM"),
        (
            "CONTA CORRENTE HSBC 12345678 E AG1234CONTA 5678",
            "CONTA CORRENTE HSBC 12345678 E AG1234CONTA 5678",
        ),
        ("CONTAS ELEITORAIS 2020 E CONTABEIS 123456", "CONTAS ELEITORAIS 2020 E CONTABEIS 123456"),
        ("MOTO 125 CC 2008", "MOTO 125 CC 2008"),
        ("MOTO 150CC 2019 E 300 CC 2008 KM", "MOTO 150CC 2019 E 300 CC 2008 KM"),
        ("CONTA 2019", "CONTA 2019"),
        ("CONTA 1234", "CONTA 1234"),
        ("CONTA 12 PARCELAS", "CONTA 12 PARCELAS"),
        ("AP 1234 BLOCO B", "AP 1234 BLOCO B"),
        ("AG 123 E AG 2008", "AG 123 E AG 2008"),
        ("PLACA AGN 1234 MOTOR CCN 12345", "PLACA AGN 1234 MOTOR CCN 12345"),
        ("CHASSI 9BWZZZ9ZCC123456", "CHASSI 9BWZZZ9ZCC123456"),
        ("CC 1.600 16V", "CC 1.600 16V"),
        ("BANCO DO BRASIL AG 1234", "BANCO DO BRASIL AG 1234"),
        ("AGENCIA 1234-5, CONTA CORRENTE", "AGENCIA 1234-5, CONTA CORRENTE"),
        ("SALDO NO BANCO CONTA 5678", "SALDO NO BANCO CONTA 5678"),
        ("AG 1234 CONTA 56789-0", "AG 1234 CONTA 56789-0"),
        ("AG 1234 C/C 56789", "AG 1234 C/C 56789"),
        ("C/C 12345", "C/C 12345"),
        ("CC 12345-6 E CC 1234-5", "CC 12345-6 E CC 1234-5"),
        ("CONTA NO BANCO EXEMPLO S/A 1234-5", "CONTA NO BANCO EXEMPLO S/A 1234-5"),
        ("AG 1234 12345-6", "AG 1234 12345-6"),
        ("CONTA 999-6", "CONTA 999-6"),
        (
            "CPF 99999999999 E 999.999.999-99 999.888.777-66",
            "CPF ***.999.999-** E ***.999.999-** ***.888.777-**",
        ),
        ("CPF/CNPJ 12345678000199", "CPF/CNPJ 12345678000199"),
        (None, None),
    ],
)
def test_mascarar_dado_pessoal_cpf_deixa_conta_e_agencia(
    db: duckdb.DuckDBPyConnection, original: str | None, expected: str | None
) -> None:
    assert one(db, "SELECT mascarar_dado_pessoal(?, 'cpf')", original) == expected


@pytest.mark.parametrize(
    ("original", "expected"),
    [
        ("PESSOA EXEMPLO 99999999999", "PESSOA EXEMPLO ***.999.999-**"),
        ("99999999999", "***.999.999-**"),
        ("***.999.999-**", "***.999.999-**"),
        ("12345678000199", "12345678000199"),
        ("EMPRESA EXEMPLO LTDA", "EMPRESA EXEMPLO LTDA"),
    ],
)
def test_mascarar_dado_pessoal_favorecido(
    db: duckdb.DuckDBPyConnection, original: str, expected: str
) -> None:
    assert one(db, "SELECT mascarar_dado_pessoal(?, 'favorecido')", original) == expected


def test_mascarar_dado_pessoal_cpf_only_masks_labelled_cpf(db: duckdb.DuckDBPyConnection) -> None:
    text = "Convoca o Sr. Pessoa Exemplo, CPF 999.999.999-99, conta 12345, ag. 1234"
    expected = "Convoca o Sr. Pessoa Exemplo, CPF ***.999.999-**, conta 12345, ag. 1234"
    assert one(db, "SELECT mascarar_dado_pessoal(?, 'cpf')", text) == expected


@pytest.mark.parametrize("modo", ["cpf", "favorecido"])
@pytest.mark.parametrize(
    ("original", "expected"),
    [
        ("Pessoa Exemplo 999.999.999-99 fez", "Pessoa Exemplo ***.999.999-** fez"),
        ("999.999.999-99", "***.999.999-**"),
        ("CPF: 99999999999 fim", "CPF: ***.999.999-** fim"),
        ("cpf 99999999999", "cpf ***.999.999-**"),
        (
            "CNPJ 12.345.678/0001-99 E ANO 2019 VALOR 1.234.567,89",
            "CNPJ 12.345.678/0001-99 E ANO 2019 VALOR 1.234.567,89",
        ),
        ("CPF:9999.999.999-99 DIGITADO COM UM A MAIS", "CPF:***.999.999-** DIGITADO COM UM A MAIS"),
        ("TITULAR999.999.999-99BEM, CIC999.999.999-999", "TITULAR***.999.999-**BEM, CIC***.999.999-**9"),
        ("SOCIO C.P.F.999.999.999-99 FIM", "SOCIO C.P.F.***.999.999-** FIM"),
        ("NUMERO 1234.567.890-12", "NUMERO 1234.567.890-12"),
    ],
)
def test_mascarar_cpf_em_todos_os_modos(
    db: duckdb.DuckDBPyConnection, modo: str, original: str, expected: str
) -> None:
    assert one(db, "SELECT mascarar_dado_pessoal(?, ?)", original, modo) == expected


TSE_VALORES = [
    None, "", "   ", "#NULO", "#NULO#", "#NE", "#NE#", "  #NE#  ", "# NE", "#JUNTOS", " #JUNTOS  A ",
    "a   b", "  Maria  ", "#nulo", "x\t\ny", "#NULO##",
]  # fmt: skip


@pytest.mark.parametrize("valor", TSE_VALORES)
def test_tse_value_equals_the_reference_rule(db: duckdb.DuckDBPyConnection, valor: str | None) -> None:
    """Regra de referência: limpa o texto; marcador do TSE ou vazio viram nulo."""
    esperado = db.execute(
        "SELECT CASE WHEN c IN ('#NULO', '#NULO#', '#NE', '#NE#') THEN NULL ELSE nullif(c, '') END "
        "FROM (SELECT clean_text(?) AS c)",
        [valor],
    ).fetchone()
    assert esperado is not None
    assert one(db, "SELECT tse_value(?)", valor) == esperado[0]


def test_tse_value_cleans_the_text_only_once(db: duckdb.DuckDBPyConnection) -> None:
    """O custo do staging do TSE está na limpeza (`regexp_replace`): ela roda uma vez por valor, não duas."""
    plano = "\n".join(
        str(r[1]) for r in db.execute("EXPLAIN SELECT tse_value(x) FROM (SELECT 'a' AS x)").fetchall()
    )
    assert plano.count("regexp_replace") <= 1, plano
