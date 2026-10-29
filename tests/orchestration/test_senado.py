"""O Senado no warehouse: pessoas, votações, votos, matérias e mandatos, sempre identificados pela fonte."""

from dado_publico_brasil.core.settings import Settings
from dado_publico_brasil.core.warehouse import Connection, scalar


def test_senators_become_people_with_standardized_names_and_empty_fields_the_source_does_not_give(
    full: tuple[Connection, Settings],
) -> None:
    con, _ = full
    row = con.execute(
        "SELECT nome, nome_civil, sexo, dt_nascimento, foto_url, qtd_propostas, qtd_votos, ultimo_partido, "
        "ultima_uf, dt_captura IS NOT NULL FROM marts.dim_pessoas_cadastro WHERE fonte = 'senado' AND nome = 'Beto Barreiras'"
    ).fetchone()
    assert row is not None
    assert row[:3] == ("Beto Barreiras", "Roberto Barreiras", "M")
    assert str(row[3]) == "1970-05-05" and row[4] == "http://foto/s5000.jpg"  # do detalhe do senador
    assert row[5:] == (None, 2, "AAA", "SP", True)
    # a Câmara informa autoria; o Senado não, e isso fica vazio em vez de zero
    assert (
        scalar(
            con,
            "SELECT COUNT(*) FROM marts.dim_pessoas_cadastro WHERE fonte = 'camara' AND qtd_propostas IS NULL",
        )
        == 0
    )


def test_a_senator_seen_only_in_the_votes_also_becomes_a_person(full: tuple[Connection, Settings]) -> None:
    con, _ = full
    assert con.execute(
        "SELECT nome, nome_civil, sexo FROM marts.dim_pessoas_cadastro WHERE fonte = 'senado' AND nome = 'Diogo'"
    ).fetchone() == ("Diogo", None, None)


def test_senate_votings_carry_the_result_the_secrecy_and_the_matter(
    full: tuple[Connection, Settings],
) -> None:
    con, _ = full
    rows = con.execute(
        "SELECT id_votacao, dt_votacao, orgao_sigla, aprovada, votos_sim, fl_votacao_secreta, proposicoes "
        "FROM marts.fct_votacoes WHERE fonte = 'senado' ORDER BY id_votacao"
    ).fetchall()
    assert [(r[0], str(r[1]), r[2], r[3], r[4], r[5], r[6]) for r in rows] == [
        ("9001", "2024-05-10", "PLEN", 1, 1, False, "PLP 700/2023"),
        ("9002", "2024-06-11", "PLEN", 0, None, True, "PLP 700/2023"),
    ]
    assert (
        scalar(
            con,
            "SELECT COUNT(*) FROM marts.fct_votacoes WHERE fonte = 'camara' AND fl_votacao_secreta IS NOT NULL",
        )
        == 0
    )


def test_senate_votes_keep_the_source_text_and_secret_ballots_stay_as_voted(
    full: tuple[Connection, Settings],
) -> None:
    con, _ = full
    votes = con.execute(
        "SELECT v.id_votacao, p.nome, v.voto, v.partido_na_fonte, v.uf FROM marts.fct_votos v JOIN marts.dim_pessoas_cadastro p USING (id_pessoa) "
        "WHERE v.fonte = 'senado' ORDER BY v.id_votacao, p.nome"
    ).fetchall()
    assert votes == [
        ("9001", "Ana Árvore", "Não", "BBB", "RJ"),
        ("9001", "Beto Barreiras", "Sim", "AAA", "SP"),
        ("9002", "Beto Barreiras", "Votou", "AAA", "SP"),
        ("9002", "Diogo", "Votou", "CCC", "MG"),
    ]


def test_each_voted_matter_appears_once_with_its_official_page(full: tuple[Connection, Settings]) -> None:
    con, _ = full
    row = con.execute(
        "SELECT sigla, ementa, ementa_oficial, dt_apresentacao, situacao, fonte_url "
        "FROM marts.fct_proposicoes WHERE fonte = 'senado' AND id_proposicao = '700'"
    ).fetchall()
    assert len(row) == 1
    sigla, ementa, oficial, apresentada, situacao, url = row[0]
    assert (sigla, str(apresentada), situacao) == (
        "PLP 700/2023",
        "2023-05-02",
        "Transformada em norma jurídica",
    )
    assert oficial == "ALTERA A LEI COMPLEMENTAR X."  # sem a quebra de linha final, caixa como veio
    assert ementa != oficial and ementa.startswith("Altera")
    assert url == "https://www25.senado.leg.br/web/atividade/materias/-/materia/700"


def test_official_exercises_come_from_the_senate_with_the_reason_each_period_ended(
    full: tuple[Connection, Settings],
) -> None:
    con, _ = full
    rows = con.execute(
        "SELECT p.nome, e.condicao_na_fonte, e.uf, e.dt_inicio, e.dt_fim, e.causa_fim "
        "FROM marts.fct_exercicios e JOIN marts.dim_pessoas_cadastro p USING (id_pessoa) "
        "WHERE e.fonte = 'senado' ORDER BY e.id_exercicio"
    ).fetchall()
    assert len(rows) == 3  # um por senador do cadastro; quem só aparece nos votos não tem exercício
    nome, condicao, uf, inicio, fim, causa = rows[0]
    assert (condicao, uf, causa) == ("Titular", "SP", "Licença")
    assert (str(inicio), str(fim)) == ("2019-02-01", "2020-05-01")


def test_raw_keeps_the_lists_as_child_tables(full: tuple[Connection, Settings]) -> None:
    con, _ = full
    assert scalar(con, "SELECT COUNT(*) FROM raw_federal_senado.votacoes__votos") == 4
    assert scalar(con, "SELECT COUNT(*) FROM raw_federal_senado.senadores__mandatos_mandato") == 3
    assert (
        scalar(
            con, "SELECT COUNT(*) FROM raw_federal_senado.senadores__mandatos_mandato__exercicios__exercicio"
        )
        == 3
    )
