"""O documento de cobertura e lacunas sai do warehouse (ADR 0054, item 4): nenhum número é digitado à mão."""

from pathlib import Path

import duckdb

from dado_publico_brasil.core.settings import Settings
from dado_publico_brasil.core.warehouse import Connection, scalar
from dado_publico_brasil.transformation import cobertura

DOC = Path(__file__).resolve().parents[2] / "docs" / "03-consultar" / "04-cobertura-e-lacunas.md"


def test_every_number_of_the_document_comes_from_the_warehouse(full: tuple[Connection, Settings]) -> None:
    con = full[0]
    con.execute("DELETE FROM marts.fct_fontes_ocorrencias")
    con.execute(
        "INSERT INTO marts.fct_fontes_ocorrencias (fonte, id_verificacao, dataset, particao, tipo_ocorrencia, "
        "dt_primeira_observacao, dt_ultima_observacao, qtd_observacoes, fl_em_aberto) VALUES "
        "('a', 7, 'd', 2024, 'indisponivel', '2024-01-01 10:00', '2024-01-02 10:00', 2, true), "
        "('a', 3, 'd', 2023, 'bloqueio', '2023-05-01 10:00', '2023-05-01 10:00', 1, false)"
    )
    con.execute("DELETE FROM metadata.fontes_verificacoes")
    con.execute(
        "INSERT INTO metadata.fontes_verificacoes (dt_verificacao, fonte, dataset, verificacao, resultado) "
        "VALUES ('2024-01-02 10:00', 'a', 'd', 'availability', 'error')"
    )
    con.execute("DELETE FROM metadata.testes_resultados")
    con.execute(
        "INSERT INTO metadata.testes_resultados (id_execucao, id_no, tipo, resultado, qtd_falhas, dt_registro) "
        "VALUES (1, 'test.p.pessoas_sem_foto', 'test', 'warn', 12, now()), "
        "(1, 'test.p.ja_corrigido', 'test', 'warn', 5, now()), (2, 'test.p.ja_corrigido', 'test', 'pass', 0, now())"
    )
    text = cobertura.markdown(con)
    assert "em 2024-01-02 10:00 UTC" in text
    assert "| a | d | 2024 | indisponivel | 2024-01-01 | 2 | 7 |" in text  # só a ocorrência em aberto
    assert "2023" not in text.split("## Ocorrências por fonte")[0]  # a encerrada só entra no histórico
    assert "| a | bloqueio | 1 | 0 |" in text and "| a | indisponivel | 1 | 1 |" in text
    assert "| pessoas_sem_foto | warn | 12 |" in text  # a lacuna medida pelo teste
    assert "ja_corrigido" not in text  # o último resultado passou
    assert scalar(con, "SELECT count(*) FROM marts.fct_fontes_ocorrencias") == 2
    assert text == cobertura.markdown(con)  # determinístico: nada de "hoje" no texto


def test_the_committed_document_is_the_generated_one() -> None:
    """Em dia: o arquivo é a saída de `dado-publico gaps`. Compara com o warehouse real, quando houver
    (a máquina de quem gera e publica); na esteira, que não tem o warehouse, confere só o cabeçalho gerado."""
    text = DOC.read_text(encoding="utf-8")
    assert text.startswith(f"{cobertura.TITLE}\n\n{cobertura.INTRO}\n"), "rode `uv run dado-publico gaps`"
    settings = Settings()
    if not settings.warehouse.exists():
        return
    from dado_publico_brasil.core import warehouse

    try:
        con = warehouse.connect(settings, read_only=True)
    except duckdb.IOException:
        return  # outro processo escreve no warehouse agora
    try:
        if (
            scalar(con, "SELECT count(*) FROM duckdb_tables() WHERE table_name = 'fct_fontes_ocorrencias'")
            == 0
        ):
            return  # o warehouse ainda não tem as medições: o dbt as cria
        assert text == cobertura.markdown(con) + "\n", (
            "docs/03-consultar/04-cobertura-e-lacunas.md desatualizado: rode `uv run dado-publico gaps`"
        )
    finally:
        con.close()
