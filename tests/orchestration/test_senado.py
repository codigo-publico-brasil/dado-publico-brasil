"""O Senado no warehouse: pessoas, votações, votos, matérias e mandatos, sempre identificados pela fonte."""

from plataforma_dados.core.settings import Settings
from plataforma_dados.core.warehouse import Connection, scalar


def test_senators_become_people_with_standardized_names_and_empty_fields_the_source_does_not_give(
    full: tuple[Connection, Settings],
) -> None:
    con, _ = full
    row = con.execute(
        "SELECT nome, nome_civil, sexo, data_nascimento, foto_url, qtd_propostas, qtd_votos, ultimo_partido, "
        "ultima_uf, capturado_em IS NOT NULL FROM marts.pessoas WHERE fonte = 'senado' AND nome = 'Beto Barreiras'"
    ).fetchone()
    assert row is not None
    assert row[:3] == ("Beto Barreiras", "Roberto Barreiras", "M")
    assert str(row[3]) == "1970-05-05" and row[4] == "http://foto/s5000.jpg"  # do detalhe do senador
    assert row[5:] == (None, 2, "AAA", "SP", True)
    # a Câmara informa autoria; o Senado não, e isso fica vazio em vez de zero
    assert (
        scalar(con, "SELECT COUNT(*) FROM marts.pessoas WHERE fonte = 'camara' AND qtd_propostas IS NULL")
        == 0
    )


def test_a_senator_seen_only_in_the_votes_also_becomes_a_person(full: tuple[Connection, Settings]) -> None:
    con, _ = full
    assert con.execute(
        "SELECT nome, nome_civil, sexo FROM marts.pessoas WHERE fonte = 'senado' AND nome = 'Diogo'"
    ).fetchone() == ("Diogo", None, None)


def test_senate_votings_carry_the_result_the_secrecy_and_the_matter(
    full: tuple[Connection, Settings],
) -> None:
    con, _ = full
    rows = con.execute(
        "SELECT votacao_id, data, orgao_sigla, aprovada, votos_sim, votacao_secreta, proposicoes "
        "FROM marts.votacoes WHERE fonte = 'senado' ORDER BY votacao_id"
    ).fetchall()
    assert [(r[0], str(r[1]), r[2], r[3], r[4], r[5], r[6]) for r in rows] == [
        ("9001", "2024-05-10", "PLEN", 1, 1, False, "PLP 700/2023"),
        ("9002", "2024-06-11", "PLEN", 0, None, True, "PLP 700/2023"),
    ]
    assert (
        scalar(
            con, "SELECT COUNT(*) FROM marts.votacoes WHERE fonte = 'camara' AND votacao_secreta IS NOT NULL"
        )
        == 0
    )


def test_senate_votes_keep_the_source_text_and_secret_ballots_stay_as_voted(
    full: tuple[Connection, Settings],
) -> None:
    con, _ = full
    votes = con.execute(
        "SELECT v.votacao_id, p.nome, v.voto, v.partido, v.uf FROM marts.votos v JOIN marts.pessoas p USING (id_pessoa) "
        "WHERE v.fonte = 'senado' ORDER BY v.votacao_id, p.nome"
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
        "SELECT sigla, ementa, ementa_oficial, apresentada_em, situacao, fonte_url "
        "FROM marts.proposicoes WHERE fonte = 'senado' AND proposicao_id = '700'"
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


def test_senate_mandates_come_from_observed_votes_with_the_official_legislature_dates(
    full: tuple[Connection, Settings],
) -> None:
    con, _ = full
    row = con.execute(
        "SELECT m.cargo, m.casa, m.legislatura_id, m.uf, m.inicio, m.legislatura_inicio, m.base "
        "FROM marts.mandatos m JOIN marts.pessoas p USING (id_pessoa) "
        "WHERE m.fonte = 'senado' AND p.nome = 'Beto Barreiras'"
    ).fetchone()
    assert row is not None
    assert row[:4] == ("Senador", "Senado Federal", 57, "SP")
    assert row[4] is None  # o início do mandato de cada pessoa a fonte não informa neste arquivo
    assert str(row[5]) == "2023-02-01"


def test_official_exercises_come_from_the_senate_with_the_reason_each_period_ended(
    full: tuple[Connection, Settings],
) -> None:
    con, _ = full
    rows = con.execute(
        "SELECT p.nome, e.participacao, e.uf, e.mandato_inicio, e.mandato_fim, e.inicio, e.fim, e.causa_afastamento "
        "FROM marts.exercicios e JOIN marts.pessoas p USING (id_pessoa) ORDER BY e.exercicio_id"
    ).fetchall()
    assert len(rows) == 3  # um por senador do cadastro; quem só aparece nos votos não tem exercício
    nome, participacao, uf, mandato_inicio, mandato_fim, inicio, fim, causa = rows[0]
    assert (participacao, uf, causa) == ("Titular", "SP", "Licença")
    assert (str(mandato_inicio), str(mandato_fim), str(inicio), str(fim)) == (
        "2019-02-01",
        "2027-01-31",
        "2019-02-01",
        "2020-05-01",
    )


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
