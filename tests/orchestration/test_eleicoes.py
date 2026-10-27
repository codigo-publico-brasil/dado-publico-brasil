"""Modelo de dados do ADR 0030 (F1 e F2): catálogos do core, fatos das eleições e fotos oficiais do TSE."""

from dado_publico_brasil.core.settings import Settings
from dado_publico_brasil.core.warehouse import Connection, rows, scalar
from dado_publico_brasil.ingestion import photos

Env = tuple[Connection, Settings]


def test_the_core_catalogs_are_loaded_and_every_office_has_its_legal_rule(full: Env) -> None:
    con, _ = full
    assert scalar(con, "SELECT COUNT(*) FROM core.cargos") == 13
    assert scalar(con, "SELECT COUNT(*) FROM core.cargos WHERE regra_legal NOT LIKE '%art.%'") == 0
    assert scalar(con, "SELECT COUNT(*) FROM core.evento_tipos") == 25
    assert scalar(con, "SELECT COUNT(*) FROM core.territorios WHERE tipo = 'pais'") == 1


def test_every_vacancy_of_the_tse_file_is_a_dispute_with_its_territory(full: Env) -> None:
    con, _ = full
    assert scalar(con, "SELECT COUNT(*) FROM core.disputas") == scalar(
        con, "SELECT COUNT(*) FROM staging.stg_tse__vagas"
    )
    rj = rows(
        con,
        "SELECT d.qtd_vagas, t.sigla FROM core.disputas d JOIN core.territorios t USING (id_territorio) "
        "JOIN core.eleicoes e USING (id_eleicao) WHERE d.id_cargo = 'deputado_federal' AND d.ue = 'RJ' "
        "AND e.ano_eleicao = 2022",
    )
    assert [(r["qtd_vagas"], r["sigla"]) for r in rj] == [(1, "RJ")]


def test_the_facts_hold_every_candidacy_including_councillors_and_link_them_to_the_dispute(full: Env) -> None:
    con, _ = full
    assert scalar(con, "SELECT COUNT(*) FROM fatos.candidaturas") == scalar(
        con, "SELECT COUNT(DISTINCT id_candidatura) FROM staging.stg_tse__candidaturas"
    )
    bia = rows(
        con,
        "SELECT c.fl_eleito, d.id_cargo FROM fatos.candidaturas c JOIN core.disputas d USING (id_disputa) "
        "WHERE c.sq_candidato = 1001 AND c.id_candidatura LIKE '2022:%'",
    )
    assert [(r["fl_eleito"], r["id_cargo"]) for r in bia] == [(True, "deputado_federal")]


def test_the_official_photo_is_listed_and_only_for_the_candidate_in_the_package(full: Env) -> None:
    con, _ = full
    found = rows(
        con,
        "SELECT sq_candidato, foto_caminho, foto_pacote_url FROM fatos.candidaturas "
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
            "SELECT COUNT(*) FROM fatos.campanhas WHERE qtd_receitas = 0 OR qtd_despesas = 0 OR qtd_bens = 0",
        )
        == 0
    )
