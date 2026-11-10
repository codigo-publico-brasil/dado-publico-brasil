"""Licitações do Portal da Transparência: um zip mensal com quatro CSVs; CPF de vencedor e participante só no raw (privado)."""

from dado_publico_brasil.core.settings import Settings
from dado_publico_brasil.core.warehouse import Connection, scalar
from dado_publico_brasil.ingestion import contract as contracts

Env = tuple[Connection, Settings]
TABELAS = ("licitacoes", "licitacoes_itens", "licitacoes_participantes", "licitacoes_empenhos")


def test_the_four_csvs_share_one_zip_per_month_and_match_by_the_start_of_the_name() -> None:
    contrato = contracts.find("transparencia")
    urls = {contrato.url(nome, 202401).partition("#")[0] for nome in TABELAS}
    assert urls == {
        "https://dadosabertos-download.cgu.gov.br/PortalDaTransparencia/saida/licitacoes/202401_Licitacoes.zip"
    }
    for nome in TABELAS:
        dataset = contrato.datasets[nome]
        assert (dataset.partition, dataset.first_month, dataset.lag_months) == ("month", 202211, 1)
    # o nome do membro tem acento (e o zip pode vir em outra codificação): casa só o começo
    assert contrato.datasets["licitacoes"].member == "*_Licita*.csv"


def test_each_csv_reaches_its_own_raw_table(full: Env) -> None:
    con, _ = full
    for tabela, por_mes in (
        ("licitacoes", 2),
        ("licitacoes_itens", 2),
        ("licitacoes_participantes", 2),
        ("licitacoes_empenhos", 1),
    ):
        por_captura = con.execute(
            f"SELECT count(*) FROM raw_federal_transparencia.{tabela} GROUP BY _source_file_id"
        ).fetchall()
        assert len(por_captura) == 12 and {n for (n,) in por_captura} == {por_mes}, tabela


def test_staging_converts_types_and_builds_the_licitacao_key(full: Env) -> None:
    con, _ = full
    found = con.execute(
        "SELECT id_licitacao, dt_resultado, dt_abertura, valor, objeto FROM marts.fct_licitacoes ORDER BY numero"
    ).fetchall()
    primeira, segunda = found
    assert primeira[0] == "200384-5-000012024"
    assert (str(primeira[1]), str(primeira[2]), float(primeira[3])) == ("2024-01-24", "2024-01-10", 205690.5)
    assert "123.456.789-09" not in primeira[4] and "***.456.789-**" in primeira[4]
    assert segunda[2] is None  # sem abertura na fonte: fica vazio


def test_the_repeated_month_keeps_one_licitacao_but_the_children_keep_every_source_row(full: Env) -> None:
    con, _ = full
    assert (
        scalar(con, "SELECT COUNT(*) FROM marts.fct_licitacoes") == 2
    )  # o mesmo pacote nos 12 meses de 2024
    assert scalar(con, "SELECT COUNT(*) FROM marts.fct_licitacoes_itens") == 24
    assert scalar(con, "SELECT COUNT(*) FROM marts.fct_licitacoes_participantes") == 24
    assert scalar(con, "SELECT COUNT(*) FROM marts.brg_licitacoes_empenhos") == 12
    assert scalar(con, "SELECT COUNT(DISTINCT id_licitacao) FROM marts.fct_licitacoes_itens") == 2


def test_the_person_cpf_never_leaves_the_raw_whole_and_the_row_is_flagged(full: Env) -> None:
    con, _ = full
    cpf = "[0-9]{3}[.]?[0-9]{3}[.]?[0-9]{3}-?[0-9]{2}"
    for tabela, texto in (
        ("fct_licitacoes_itens", "item || ' ' || cd_vencedor || ' ' || vencedor"),
        ("fct_licitacoes_participantes", "cd_participante || ' ' || participante"),
    ):
        assert (
            scalar(
                con,
                f"SELECT COUNT(*) FROM marts.{tabela} WHERE regexp_matches({texto}, '(^|[^0-9]){cpf}($|[^0-9])')",
            )
            == 0
        ), tabela
    marcadas = con.execute(
        "SELECT DISTINCT cd_participante, fl_vencedor FROM marts.fct_licitacoes_participantes "
        "WHERE fl_contem_dado_pessoal"
    ).fetchall()
    assert marcadas == [("***.456.789-**", False)]
    assert scalar(con, "SELECT COUNT(*) FROM marts.fct_licitacoes_itens WHERE fl_contem_dado_pessoal") == 12


def test_the_winner_flag_is_boolean_and_every_row_points_to_its_capture(full: Env) -> None:
    con, _ = full
    assert {
        v
        for (v,) in con.execute(
            "SELECT DISTINCT fl_vencedor FROM marts.fct_licitacoes_participantes"
        ).fetchall()
    } == {True, False}
    for modelo in (
        "fct_licitacoes",
        "fct_licitacoes_itens",
        "fct_licitacoes_participantes",
        "brg_licitacoes_empenhos",
    ):
        assert scalar(con, f"SELECT COUNT(*) FROM marts.{modelo} WHERE id_captura IS NULL") == 0
