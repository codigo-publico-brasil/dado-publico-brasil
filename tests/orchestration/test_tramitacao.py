"""Tramitação (Câmara) e processo (Senado) buscados por item: dados nos marts e auditoria do landing."""

from plataforma_dados.core.settings import Settings
from plataforma_dados.core.warehouse import Connection, scalar
from plataforma_dados.ingestion import contract, foreach

Env = tuple[Connection, Settings]


def test_camara_andamentos_come_in_order_with_standardized_situation(full: Env) -> None:
    con, _ = full
    rows = con.execute(
        "SELECT sequencia, orgao_sigla, situacao, despacho FROM marts.tramitacoes "
        "WHERE fonte = 'camara' AND proposicao_id = '100' ORDER BY sequencia"
    ).fetchall()
    assert [(r[0], r[1], r[2]) for r in rows] == [
        (1, "MESA", "Aguardando designação"),
        (2, "CCJC", "Aguardando parecer"),
        (3, "PLEN", "Transformado em norma jurídica"),
    ]
    assert rows[0][3] == "Apresentação da proposição 100."


def test_only_the_fetched_target_items_have_andamentos_and_the_rest_is_measured(full: Env) -> None:
    con, _ = full
    assert scalar(con, "SELECT COUNT(DISTINCT proposicao_id) FROM marts.tramitacoes") == 2  # 100 e 101
    gap = scalar(
        con,
        "SELECT failures FROM metadata.dbt_results WHERE unique_id LIKE '%proposicoes_alvo_sem_tramitacao%'",
    )
    assert gap == 1  # a 102 é PL, mas a fonte respondeu 404


def test_senate_process_gives_the_current_situation_and_the_norm_that_resulted(full: Env) -> None:
    con, _ = full
    row = con.execute(
        "SELECT situacao, ultimo_status_em FROM marts.proposicoes WHERE fonte = 'senado' AND proposicao_id = '700'"
    ).fetchone()
    assert row is not None and row[0] == "Transformada em norma jurídica" and str(row[1]) == "2024-07-01"
    norm = con.execute(
        "SELECT proposicao_id, tipo, numero, ano, assinada_em, publicada_em, descricao, veiculo_publicacao "
        "FROM marts.normas_geradas"
    ).fetchall()
    assert [(n[0], n[1], n[2], n[3], str(n[4]), str(n[5]), n[6], n[7]) for n in norm] == [
        (
            "700",
            "Lei Complementar",
            220,
            2024,
            "2024-06-28",
            "2024-07-01",
            "Lei Complementar nº 220 de 28/06/2024",
            "DOU",
        )
    ]


def test_raw_keeps_the_list_of_authors_of_the_process_as_a_child_table(full: Env) -> None:
    con, _ = full
    assert scalar(con, "SELECT COUNT(*) FROM raw_federal_senado.processos__autoria_iniciativa") == 1


def test_the_whole_landing_verifies_and_each_item_is_indexed(full: Env) -> None:
    con, settings = full
    assert foreach.verify(con, settings) == []  # arquivos, respostas dentro dos lotes e índice conferem
    assert scalar(con, "SELECT COUNT(*) FROM metadata.capture_items WHERE source = 'camara'") == 3
    assert scalar(con, "SELECT COUNT(*) FROM metadata.capture_items WHERE status = 404") == 1


def test_coverage_is_reported_per_dataset(full: Env) -> None:
    con, _ = full
    camara = contract.find("camara")
    assert foreach.coverage(con, camara, "proposicoes_tramitacoes") == {
        "esperados": 3,
        "obtidos": 2,
        "inexistentes": 1,
        "falhas": 0,
        "faltam": 0,
    }
