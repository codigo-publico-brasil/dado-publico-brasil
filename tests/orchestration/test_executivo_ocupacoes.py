"""Topo do Executivo federal (PEP): só presidente, vice e ministro entram; o CPF nunca; a data ausente fica vazia."""

from dado_publico_brasil.core.settings import Settings
from dado_publico_brasil.core.warehouse import Connection, scalar
from dado_publico_brasil.ingestion import contract as contracts
from dado_publico_brasil.ingestion.custom.executivo.federal import pep

Env = tuple[Connection, Settings]


def test_the_contract_keeps_no_document_and_one_file_per_month() -> None:
    dataset = contracts.find("pep").datasets["dirigentes"]
    assert not [c for c in dataset.columns if "cpf" in c.lower()]
    assert (dataset.partition, dataset.first_month, dataset.lag_months) == ("month", 202609, 1)


def test_the_raw_drops_every_row_outside_the_top_of_the_executive(full: Env) -> None:
    con, _ = full
    funcoes = {
        f for (f,) in con.execute("SELECT DISTINCT descri_o_fun_o FROM raw_federal_pep.dirigentes").fetchall()
    }
    assert funcoes == {"PRESIDENTE DA REPUBLICA", "VICE-PRESIDENTE DA REPUBLICA", "MINISTRO DE ESTADO"}


def test_the_mart_has_one_row_per_occupation_even_when_every_month_repeats_it(full: Env) -> None:
    con, _ = full
    assert scalar(con, "SELECT COUNT(DISTINCT id_captura) FROM staging.stg_pep__dirigentes") >= 2
    assert scalar(con, "SELECT COUNT(*) FROM marts.fct_executivo_ocupacoes") == 6
    assert scalar(con, "SELECT COUNT(DISTINCT id_ocupacao_executivo) FROM marts.fct_executivo_ocupacoes") == 6


def test_missing_dates_stay_empty_and_the_source_is_traceable(full: Env) -> None:
    con, _ = full
    linhas = {
        nome: (str(i), None if f is None else str(f))
        for nome, i, f in con.execute(
            "SELECT nome, dt_inicio, dt_fim FROM marts.fct_executivo_ocupacoes WHERE dt_inicio IS NOT NULL"
        ).fetchall()
    }
    assert linhas["Pessoa Exemplo A"] == ("2019-01-01", "2023-01-01")
    assert linhas["Pessoa Exemplo B"][1] is None  # "Não informada" não vira data
    assert scalar(con, "SELECT COUNT(*) FROM marts.fct_executivo_ocupacoes WHERE dt_inicio IS NULL") == 1
    assert scalar(con, "SELECT COUNT(*) FROM marts.fct_executivo_ocupacoes WHERE id_captura IS NULL") == 0


def test_a_403_of_a_withdrawn_month_is_a_plain_failure_not_a_block(monkeypatch, tmp_path) -> None:  # type: ignore[no-untyped-def]
    from dado_publico_brasil.ingestion import fetch

    def blocked(*args: object, **kwargs: object) -> None:
        raise fetch.SourceBlocked("x: HTTP 403", 403)

    monkeypatch.setattr(fetch, "download", blocked)
    try:
        pep.download("https://exemplo/202608_PEP.zip", tmp_path)
    except OSError as error:
        assert "retirado" in str(error)
    else:
        raise AssertionError("403 deveria virar OSError")

    def throttled(*args: object, **kwargs: object) -> None:
        raise fetch.SourceBlocked("x: HTTP 429", 429)

    monkeypatch.setattr(fetch, "download", throttled)
    try:
        pep.download("https://exemplo/202608_PEP.zip", tmp_path)
    except fetch.SourceBlocked:
        pass
    else:
        raise AssertionError("429 continua sendo bloqueio")
