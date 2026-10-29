"""Modelo de dados do ADR 0030 (F1 e F2): catálogos do core, fatos das eleições e fotos oficiais do TSE."""

from dado_publico_brasil.core.settings import Settings
from dado_publico_brasil.core.warehouse import Connection, rows, scalar
from dado_publico_brasil.ingestion import photos

Env = tuple[Connection, Settings]


def test_the_core_catalogs_are_loaded_and_every_office_has_its_legal_rule(full: Env) -> None:
    con, _ = full
    assert scalar(con, "SELECT COUNT(*) FROM marts.dim_cargos") == 13
    assert scalar(con, "SELECT COUNT(*) FROM marts.dim_cargos WHERE regra_legal NOT LIKE '%art.%'") == 0
    assert scalar(con, "SELECT COUNT(*) FROM marts.dim_evento_tipos") == 25
    assert scalar(con, "SELECT COUNT(*) FROM marts.dim_territorios WHERE tipo = 'pais'") == 1


def test_every_vacancy_of_the_tse_file_is_a_dispute_with_its_territory(full: Env) -> None:
    con, _ = full
    assert scalar(con, "SELECT COUNT(*) FROM marts.dim_disputas") == scalar(
        con, "SELECT COUNT(*) FROM staging.stg_tse__vagas"
    )
    rj = rows(
        con,
        "SELECT d.qtd_vagas, t.sigla FROM marts.dim_disputas d JOIN marts.dim_territorios t USING (id_territorio) "
        "JOIN marts.dim_eleicoes e USING (id_eleicao) WHERE d.id_cargo = 'deputado_federal' AND d.ue = 'RJ' "
        "AND e.ano_eleicao = 2022",
    )
    assert [(r["qtd_vagas"], r["sigla"]) for r in rj] == [(1, "RJ")]


def test_the_facts_hold_every_candidacy_including_councillors_and_link_them_to_the_dispute(full: Env) -> None:
    con, _ = full
    assert scalar(con, "SELECT COUNT(*) FROM marts.fct_candidaturas") == scalar(
        con, "SELECT COUNT(DISTINCT id_candidatura) FROM staging.stg_tse__candidaturas"
    )
    bia = rows(
        con,
        "SELECT c.fl_eleito, d.id_cargo FROM marts.fct_candidaturas c JOIN marts.dim_disputas d USING (id_disputa) "
        "WHERE c.sq_candidato = 1001 AND c.id_candidatura LIKE '2022:%'",
    )
    assert [(r["fl_eleito"], r["id_cargo"]) for r in bia] == [(True, "deputado_federal")]


def test_the_official_photo_is_listed_and_only_for_the_candidate_in_the_package(full: Env) -> None:
    con, _ = full
    found = rows(
        con,
        "SELECT sq_candidato, foto_caminho, foto_pacote_url FROM marts.fct_candidaturas "
        "WHERE foto_arquivo IS NOT NULL",
    )
    assert [(r["sq_candidato"], r["foto_caminho"]) for r in found] == [(1001, "2022/RJ/1001.jpg")]
    assert str(found[0]["foto_pacote_url"]).endswith("/eleicoes2022/fotos/foto_cand2022_RJ_div.zip")


def test_extracting_the_photos_writes_each_image_once(full: Env) -> None:
    con, settings = full
    assert photos.extract_all(con, settings) == 1
    assert (settings.storage_root / "fotos" / "2022" / "RJ" / "1001.jpg").read_bytes().startswith(b"\xff\xd8")
    assert photos.extract_all(con, settings) == 0


def test_a_campaign_total_is_empty_not_zero_when_the_file_has_no_data(full: Env) -> None:
    con, _ = full
    assert (
        scalar(
            con,
            "SELECT COUNT(*) FROM marts.fct_campanhas WHERE qtd_receitas = 0 OR qtd_despesas = 0 OR qtd_bens = 0",
        )
        == 0
    )
