"""Municípios do IBGE e o de-para com o código de município do TSE."""

from dado_publico_brasil.core.settings import Settings
from dado_publico_brasil.core.warehouse import Connection, scalar

Env = tuple[Connection, Settings]


def test_the_ibge_list_is_the_territorial_dimension_with_the_official_code_and_the_region(full: Env) -> None:
    con, _ = full
    assert scalar(con, "SELECT COUNT(*) FROM marts.municipios") == 3
    row = con.execute(
        "SELECT nome, uf, uf_nome, regiao_sigla, nome_busca FROM marts.municipios WHERE id_municipio = 3300001"
    ).fetchone()
    assert row == ("Município 60011", "RJ", "Rio de Janeiro", "SE", "municipio 60011")


def test_the_tse_code_links_to_the_ibge_code_by_name_and_state_and_the_method_is_recorded(full: Env) -> None:
    con, _ = full
    row = con.execute(
        "SELECT id_municipio, metodo, uf FROM marts.municipios_codigos_tse WHERE cd_municipio_tse = '60011'"
    ).fetchone()
    assert row == (3300001, "nome e UF iguais e únicos", "RJ")


def test_a_name_that_exists_in_two_states_is_never_linked_across_them(full: Env) -> None:
    con, _ = full
    # "São Paulo" existe no IBGE em SP e em RJ (sintético): a UF faz parte da chave, então nenhum vínculo cruza estados
    crossed = scalar(
        con,
        "SELECT COUNT(*) FROM marts.municipios_codigos_tse c JOIN marts.municipios m USING (id_municipio) "
        "WHERE c.uf <> m.uf",
    )
    assert crossed == 0
