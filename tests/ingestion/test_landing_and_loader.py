"""Landing (arquivos intactos com hash) e raw (carga fiel pelo dlt)."""

import hashlib
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import duckdb
import pytest
from synthetic_camara import fake_downloader, no_headers, synthetic_files

from dado_publico_brasil.core import runs, warehouse
from dado_publico_brasil.core.settings import Settings
from dado_publico_brasil.core.warehouse import Connection, columns, rows, scalar, tables
from dado_publico_brasil.ingestion import landing, loader, monitoring
from dado_publico_brasil.ingestion.contract import InvalidContract, SourceContract, load_contract


def test_extract_keeps_the_original_with_hash_and_registers_the_capture(
    con: Connection, settings: Settings, contract: SourceContract, tmp_path: Path
) -> None:
    files = synthetic_files(tmp_path / "origin")
    capture_id = landing.extract(
        con,
        settings,
        contract,
        "deputados",
        downloader=fake_downloader(files),
        head_request=no_headers,
    )
    path, sha, run_id = con.execute(
        "SELECT caminho, sha256, id_execucao FROM metadata.capturas WHERE id_captura = ?", (capture_id,)
    ).fetchone() or ("", "", 0)
    assert path.startswith("landing/camara/deputados/completo/")
    assert sha[:12] in path
    assert (settings.storage_root / path).exists()
    assert con.execute(
        "SELECT etapa, resultado FROM metadata.execucoes WHERE id_execucao = ?", (run_id,)
    ).fetchone() == (
        "extract",
        "ok",
    )


def test_extracting_twice_does_not_duplicate_the_capture(
    con: Connection, settings: Settings, contract: SourceContract, tmp_path: Path
) -> None:
    download = fake_downloader(synthetic_files(tmp_path / "origin"))
    a = landing.extract(con, settings, contract, "deputados", downloader=download, head_request=no_headers)
    b = landing.extract(con, settings, contract, "deputados", downloader=download, head_request=no_headers)
    assert a == b
    assert scalar(con, "SELECT COUNT(*) FROM metadata.capturas") == 1


def test_the_path_shows_source_dataset_reference_and_capture_date_and_the_same_content_on_another_day_is_not_kept_twice(
    con: Connection,
    settings: Settings,
    contract: SourceContract,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    download = fake_downloader(synthetic_files(tmp_path / "origin"))
    monkeypatch.setattr(runs, "now", lambda: "2026-10-01T10:00:00+00:00")
    first = landing.extract(con, settings, contract, "votacoes", 2024, download, no_headers)
    path = scalar(con, "SELECT caminho FROM metadata.capturas WHERE id_captura = ?", (first,))
    assert path.startswith("landing/camara/votacoes/2024/20261001/")
    monkeypatch.setattr(runs, "now", lambda: "2026-10-02T10:00:00+00:00")
    assert landing.extract(con, settings, contract, "votacoes", 2024, download, no_headers) == first
    assert not (settings.landing_dir / "camara" / "votacoes" / "2024" / "20261002").exists()
    assert (settings.storage_root / path).exists()


def test_unchanged_file_is_not_downloaded_again(
    con: Connection, settings: Settings, contract: SourceContract, tmp_path: Path
) -> None:
    download = fake_downloader(synthetic_files(tmp_path / "origin"))
    headers = {"etag": '"v1"', "last_modified": None, "size": None}
    landing.extract(con, settings, contract, "deputados", downloader=download, head_request=lambda u: headers)
    calls: list[str] = []

    def must_not_download(url: str, folder: Path) -> tuple[Path, str, int]:
        calls.append(url)
        raise AssertionError("não deveria baixar de novo")

    landing.extract(
        con,
        settings,
        contract,
        "deputados",
        downloader=must_not_download,
        head_request=lambda u: headers,
    )
    assert calls == []


def test_current_captures_returns_only_the_latest_of_each_url(con: Connection) -> None:
    args = ("camara", "deputados", None, "http://x/d.csv")
    landing.register_capture(con, *args, "h1", 1, "a", 1)
    latest = landing.register_capture(con, *args, "h2", 1, "b", 1)
    assert [c["id_captura"] for c in landing.current_captures(con, "camara")] == [latest]


def test_raw_has_only_allowed_columns_and_never_the_personal_document(
    raw: tuple[Connection, Settings],
) -> None:
    con, _ = raw
    cols = set(columns(con, "raw_federal_camara", "deputados"))
    assert "cpf" not in cols
    assert {"uri", "nome", "nome_civil", "_source_file_id", "_ingested_at"} <= cols
    content = " ".join(
        str(c) for row in con.execute("SELECT * FROM raw_federal_camara.deputados").fetchall() for c in row
    )
    assert "12345678900" not in content


def test_raw_is_faithful_to_the_source_and_empty_values_become_null(
    raw: tuple[Connection, Settings],
) -> None:
    con, _ = raw
    assert con.execute(
        "SELECT nome, nome_civil FROM raw_federal_camara.deputados WHERE uri LIKE '%/10'"
    ).fetchone() == (
        "ANA ÁRVORE",
        "ANA DA SILVA",
    )
    assert con.execute(
        "SELECT ultimo_status_descricao_situacao FROM raw_federal_camara.proposicoes WHERE id = '102'"
    ).fetchone() == (None,)


def test_every_raw_row_points_to_an_existing_capture(raw: tuple[Connection, Settings]) -> None:
    con, _ = raw
    for table in tables(con, "raw_federal_camara"):
        orphans = scalar(
            con,
            f"SELECT COUNT(*) FROM raw_federal_camara.{table} t "
            "WHERE NOT EXISTS (SELECT 1 FROM metadata.capturas c WHERE c.id_captura = t._source_file_id)",
        )
        assert orphans == 0, table


def test_every_raw_row_has_the_time_it_arrived(raw: tuple[Connection, Settings]) -> None:
    con, _ = raw
    for table in tables(con, "raw_federal_camara"):
        sem_data = scalar(con, f"SELECT COUNT(*) FROM raw_federal_camara.{table} WHERE _ingested_at IS NULL")
        assert sem_data == 0, table


def test_loading_again_is_idempotent(raw: tuple[Connection, Settings], contract: SourceContract) -> None:
    con, settings = raw
    before = {
        t: scalar(con, f"SELECT COUNT(*) FROM raw_federal_camara.{t}")
        for t in tables(con, "raw_federal_camara")
    }
    assert loader.load_pending(con, settings, contract) == (0, 0)  # nada novo
    loader.load_pending(con, settings, contract, rebuild=True)
    after = {
        t: scalar(con, f"SELECT COUNT(*) FROM raw_federal_camara.{t}")
        for t in tables(con, "raw_federal_camara")
    }
    assert before == after


def test_recheck_headers_reads_the_landing_files_again(
    raw: tuple[Connection, Settings], contract: SourceContract
) -> None:
    con, settings = raw
    antes = scalar(con, "SELECT COUNT(*) FROM metadata.fontes_verificacoes WHERE verificacao = 'schema'")
    assert loader.recheck_headers(con, settings, contract) > 0
    assert (
        scalar(con, "SELECT COUNT(*) FROM metadata.fontes_verificacoes WHERE verificacao = 'schema'") > antes
    )


def test_load_marks_the_capture_as_loaded(raw: tuple[Connection, Settings]) -> None:
    con, _ = raw
    assert scalar(con, "SELECT COUNT(*) FROM metadata.capturas WHERE dt_carga IS NULL") == 0


CONTRACT = """
source: teste
power: legislativo
level: municipal
description: Fonte de teste
access: {{base_url: "http://exemplo", delimiter: ",", encoding: utf-8}}
datasets:
  pessoas:
    url: "{{base_url}}/pessoas.csv"
    load: full
    write: merge
    primary_key: [codigo]
    columns: [codigo, nome{extra}]
  lancamentos:
    url: "{{base_url}}/lancamentos.csv"
    load: full
    write: merge
    primary_key: [_row_hash]
    columns: [codigo, valor]
  retratos:
    url: "{{base_url}}/retratos.csv"
    load: full
    write: replace_partition
    primary_key: [_row_hash]
    columns: [codigo, valor]
  fixos:
    url: "{{base_url}}/fixos.csv"
    load: full
    write: replace
    columns: [codigo]
"""


def make_contract(tmp_path: Path, extra: str = "") -> SourceContract:
    file = tmp_path / "contract.yml"
    file.write_text(CONTRACT.format(extra=extra), encoding="utf-8")
    return load_contract(file)


def read_all(settings: Settings, sql: str) -> list[tuple[object, ...]]:
    con = duckdb.connect(str(settings.warehouse), read_only=True)
    try:
        return con.execute(sql).fetchall()
    finally:
        con.close()


def load(
    settings: Settings,
    contract: SourceContract,
    dataset: str,
    text: str,
    file_id: int,
    superseded: tuple[int, ...] = (),
) -> dict[str, int]:
    file = settings.storage_root / f"{dataset}-{file_id}.csv"
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(text, encoding="utf-8")
    stats = loader.load_file(settings, contract, contract.datasets[dataset], file, file_id, superseded)
    con = warehouse.connect(settings)
    try:
        loader.create_views(settings, contract, con)
    finally:
        con.close()
    return stats


def test_new_source_enters_with_only_a_contract_and_rejects_rows_without_key(
    tmp_path: Path,
) -> None:
    settings = Settings(storage_root=tmp_path / "store")
    contract = make_contract(tmp_path)
    stats = load(settings, contract, "pessoas", "codigo,nome,cpf\n1,Ana,111\n2,Bia,222\n,Sem Chave,333\n", 7)
    assert stats == {
        "read": 3,
        "filtered": 0,
        "loaded": 2,
        "rejected": 1,
        "conflicting": 0,
        "replaced": 0,
        "removed": 0,
    }
    assert read_all(
        settings, "SELECT codigo, nome, _source_file_id FROM raw_municipal_teste.pessoas ORDER BY 1"
    ) == [
        ("1", "Ana", 7),
        ("2", "Bia", 7),
    ]
    assert "cpf" not in {
        c
        for (c,) in read_all(
            settings,
            "SELECT column_name FROM information_schema.columns WHERE table_name = 'pessoas'",
        )
    }


def test_adding_a_column_to_the_contract_adds_it_to_the_table(tmp_path: Path) -> None:
    settings = Settings(storage_root=tmp_path / "store")
    text = "codigo,nome,cidade\n1,Ana,Santos\n"
    load(settings, make_contract(tmp_path), "pessoas", text, 1)
    load(settings, make_contract(tmp_path, ", cidade"), "pessoas", text, 2)
    assert read_all(settings, "SELECT codigo, cidade FROM raw_municipal_teste.pessoas") == [("1", "Santos")]


def test_replace_swaps_the_previous_content(tmp_path: Path) -> None:
    settings = Settings(storage_root=tmp_path / "store")
    contract = make_contract(tmp_path)
    load(settings, contract, "fixos", "codigo\n1\n2\n", 1)
    load(settings, contract, "fixos", "codigo\n3\n", 2, (1,))
    assert read_all(settings, "SELECT codigo FROM raw_municipal_teste.fixos") == [("3",)]


def test_normalize_matches_what_the_dbt_sources_expect() -> None:
    assert loader.normalize("siglaUFAutor") == "sigla_uf_autor"
    assert loader.normalize("deputado_idLegislatura") == "deputado_id_legislatura"
    assert loader.normalize("idLegislaturaInicial") == "id_legislatura_inicial"


def test_dlt_temporary_area_does_not_look_like_the_dbt_staging_layer(
    raw: tuple[Connection, Settings],
) -> None:
    con, _ = raw
    schemas = {r[0] for r in con.execute("SELECT schema_name FROM duckdb_schemas()").fetchall()}
    assert "raw_camara_staging" not in schemas
    assert not {s for s in schemas if s.endswith("_staging")}


def test_a_natural_key_that_joins_different_rows_is_counted_as_a_collision_and_identical_repeats_are_not(
    tmp_path: Path,
) -> None:
    settings = Settings(storage_root=tmp_path / "store")
    contract = make_contract(tmp_path)
    text = "codigo,nome,cpf\n1,Ana,111\n1,Outra Ana,222\n2,Bia,333\n2,Bia,333\n"
    stats = load(settings, contract, "pessoas", text, 8)
    assert stats["read"] == 4 and stats["conflicting"] == 1  # a linha 2 repetida e idêntica não é perda


def test_identical_rows_of_the_source_are_all_kept_and_loading_again_does_not_duplicate_them(
    tmp_path: Path,
) -> None:
    settings = Settings(storage_root=tmp_path / "store")
    contract = make_contract(tmp_path)
    text = "codigo,valor\n1,10\n1,10\n1,10\n2,5\n"
    stats = load(settings, contract, "lancamentos", text, 9)
    assert stats["loaded"] == 4 and stats["conflicting"] == 0
    load(settings, contract, "lancamentos", text, 10)
    assert read_all(
        settings,
        "SELECT codigo, count(*), count(DISTINCT _row_hash) FROM raw_municipal_teste.lancamentos GROUP BY 1 ORDER BY 1",
    ) == [("1", 3, 3), ("2", 1, 1)]


def test_the_load_registers_one_balance_that_is_an_error_for_collisions_and_rejections_and_ok_otherwise(
    con: Connection,
) -> None:
    from dado_publico_brasil.ingestion import monitoring

    monitoring.check_load(
        con, "teste", "ds", 2006, {"read": 10, "filtered": 3, "loaded": 6, "rejected": 1, "conflicting": 2}
    )
    found = con.execute("SELECT verificacao, resultado, detalhe FROM metadata.fontes_verificacoes").fetchall()
    assert [(c, s) for c, s, _ in found] == [("carga", "error")]
    assert "filtradas pelo only 3" in found[0][2] and "colisões de chave 2" in found[0][2]
    monitoring.check_load(
        con, "teste", "limpo", None, {"read": 5, "filtered": 0, "loaded": 5, "rejected": 0, "conflicting": 0}
    )
    assert scalar(con, "SELECT resultado FROM metadata.fontes_verificacoes WHERE dataset = 'limpo'") == "ok"


def test_declared_tolerance_turns_the_rejection_into_a_warning_only_up_to_the_limit(con: Connection) -> None:
    from dado_publico_brasil.ingestion import monitoring
    from dado_publico_brasil.ingestion.contract import Tolerancia

    tolerance = Tolerancia(limite=1, justificativa="linha da fonte sem chave")
    stats = {"read": 10, "filtered": 0, "loaded": 9, "rejected": 1, "conflicting": 0}

    def outcome(values: dict[str, int], declared: Tolerancia | None) -> tuple[str, str]:
        con.execute("DELETE FROM metadata.fontes_verificacoes")
        monitoring.check_load(con, "teste", "ds", 2004, values, declared)
        return con.execute("SELECT resultado, detalhe FROM metadata.fontes_verificacoes").fetchall()[0]

    status, detail = outcome(stats, tolerance)
    assert status == "warn" and "rejeitadas 1" in detail and "tolerada: linha da fonte sem chave" in detail
    assert outcome({**stats, "loaded": 8, "rejected": 2}, tolerance)[0] == "error"
    assert outcome({**stats, "conflicting": 1}, tolerance)[0] == "error"
    assert outcome(stats, None)[0] == "error"  # sem declaração, o comportamento não muda


def test_rows_that_a_previous_capture_had_and_the_current_one_lacks_are_a_warning_and_leave_the_raw(
    con: Connection, settings: Settings, tmp_path: Path
) -> None:
    contract = make_contract(tmp_path)

    def capture(text: str, sha: str) -> dict[str, object]:
        file = settings.storage_root / f"landing/{sha}.csv"
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(text, encoding="utf-8")
        url = contract.url("pessoas")
        landing.register_capture(con, "teste", "pessoas", None, url, sha, len(text), f"landing/{sha}.csv", 1)
        return rows(con, "SELECT * FROM metadata.capturas WHERE sha256 = ?", (sha,))[0]

    def checks() -> list[tuple[str, str]]:
        return con.execute(
            "SELECT resultado, detalhe FROM metadata.fontes_verificacoes WHERE verificacao = 'linhas_removidas' ORDER BY id_verificacao"
        ).fetchall()

    loader.load_capture(con, settings, contract, capture("codigo,nome\n1,Ana\n2,Bia\n", "a"))
    assert checks() == []  # primeira captura: nada a comparar
    loader.load_capture(con, settings, contract, capture("codigo,nome\n1,Ana\n", "b"))
    assert [(s, d[:8]) for s, d in checks()] == [("warn", "1 linhas")]
    loader.create_views(settings, contract, con)
    assert scalar(con, "SELECT count(*) FROM raw_municipal_teste.pessoas") == 1  # a linha 2 saiu do raw
    loader.load_capture(con, settings, contract, capture("codigo,nome\n1,Ana\n3,Cid\n", "c"))
    assert [s for s, _ in checks()][-1] == "ok"  # o que a anterior tinha, a atual ainda traz


def test_reset_lets_a_table_be_reloaded_when_the_contract_changes_the_primary_key(tmp_path: Path) -> None:
    settings = Settings(storage_root=tmp_path / "store")
    contract = make_contract(tmp_path)
    load(settings, contract, "pessoas", "codigo,nome\n1,Ana\n2,Bia\n", 1)
    file = tmp_path / "contract.yml"  # a chave passa a ser o conteúdo da linha
    file.write_text(
        file.read_text(encoding="utf-8").replace("primary_key: [codigo]", "primary_key: [_row_hash]")
    )
    changed = load_contract(file)
    loader.reset_dataset(settings, changed, changed.datasets["pessoas"])
    load(settings, changed, "pessoas", "codigo,nome\n1,Ana\n1,Ana\n3,Caio\n", 2)
    assert read_all(
        settings, "SELECT codigo, nome, _source_file_id FROM raw_municipal_teste.pessoas ORDER BY 1"
    ) == [
        ("1", "Ana", 2),
        ("1", "Ana", 2),
        ("3", "Caio", 2),
    ]  # nada da carga anterior sobrou, e as linhas idênticas da fonte ficam todas


def _capture(
    con: Connection, settings: Settings, contract: SourceContract, url: str, text: str, sha: str
) -> dict[str, Any]:
    file = settings.storage_root / f"landing/{sha}.csv"
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(text, encoding="utf-8")
    landing.register_capture(con, "teste", "retratos", None, url, sha, len(text), f"landing/{sha}.csv", 1)
    return rows(con, "SELECT * FROM metadata.capturas WHERE sha256 = ?", (sha,))[0]


def test_replace_partition_swaps_only_the_rows_of_the_same_file_and_is_idempotent(
    con: Connection, settings: Settings, tmp_path: Path
) -> None:
    contract = make_contract(tmp_path)
    table = "raw_municipal_teste.retratos"

    def values() -> list[tuple[Any, ...]]:
        loader.create_views(settings, contract, con)
        return con.execute(f"SELECT _source_file_id, codigo FROM {table} ORDER BY 1, 2").fetchall()

    a1 = _capture(con, settings, contract, "http://x/a", "codigo,valor\n1,10\n2,20\n2,20\n", "a1")
    b1 = _capture(con, settings, contract, "http://x/b", "codigo,valor\n9,90\n", "b1")
    loader.load_capture(con, settings, contract, a1)
    loader.load_capture(con, settings, contract, b1)
    assert len(values()) == 4  # as linhas idênticas da fonte ficam todas
    a2 = _capture(con, settings, contract, "http://x/a", "codigo,valor\n2,20\n3,30\n", "a2")
    for _ in range(2):  # carregar a mesma captura de novo não duplica
        loader.load_capture(con, settings, contract, a2)
        assert values() == [
            (b1["id_captura"], "9"),
            (a2["id_captura"], "2"),
            (a2["id_captura"], "3"),
        ]
    assert (
        scalar(
            con, "SELECT count(*) FROM metadata.fontes_verificacoes WHERE verificacao = 'linhas_removidas'"
        )
        == 0
    )


def test_replace_partition_does_not_accept_nested_lists(tmp_path: Path) -> None:
    file = tmp_path / "c.yml"
    file.write_text(
        CONTRACT.format(extra="").replace(
            "write: replace_partition", "write: replace_partition\n    nested: [codigo]"
        ),
        encoding="utf-8",
    )
    with pytest.raises(InvalidContract, match="replace_partition"):
        load_contract(file)


def test_the_load_reports_file_size_rows_and_time_through_the_log_callback(
    con: Connection, settings: Settings, tmp_path: Path
) -> None:
    contract = make_contract(tmp_path)
    capture = _capture(con, settings, contract, "http://x/a", "codigo,valor\n1,10\n2,20\n", "log1")
    messages: list[str] = []
    loader.load_pending(con, settings, contract, log=messages.append)
    text = "\n".join(messages)
    assert "retratos: carga de log1.csv" in text and "MB" in text
    assert "2 linhas carregadas de 2 lidas" in text and "capturas e 2 linhas carregadas no raw" in text
    assert capture["id_captura"]


def _capture_of(
    con: Connection, settings: Settings, dataset: str, url: str, text: str, sha: str
) -> dict[str, Any]:
    file = settings.storage_root / f"landing/{sha}.csv"
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(text, encoding="utf-8")
    landing.register_capture(con, "teste", dataset, None, url, sha, len(text), f"landing/{sha}.csv", 1)
    return rows(con, "SELECT * FROM metadata.capturas WHERE sha256 = ?", (sha,))[0]


def test_every_raw_dataset_has_its_view_even_without_a_capture_and_a_later_load_fits_it(
    con: Connection, settings: Settings, tmp_path: Path
) -> None:
    contract = make_contract(tmp_path)
    loader.create_views(settings, contract, con)
    loader.create_views(settings, contract, con)  # idempotente
    pessoas = [c[0] for c in con.execute("DESCRIBE SELECT * FROM raw_municipal_teste.pessoas").fetchall()]
    assert {"codigo", "nome", "_source_file_id", "_ingested_at", "_dlt_load_id", "_dlt_id"} <= set(pessoas)
    assert "_row_hash" in [
        c[0] for c in con.execute("DESCRIBE SELECT * FROM raw_municipal_teste.lancamentos").fetchall()
    ]
    for name in ("pessoas", "lancamentos", "retratos", "fixos"):
        assert scalar(con, f"SELECT count(*) FROM raw_municipal_teste.{name}") == 0
    capture = _capture_of(con, settings, "pessoas", "http://x/p", "codigo,nome\n1,Ana\n2,Bia\n", "p1")
    loader.load_capture(con, settings, contract, capture)  # sem erro de esquema sobre a view vazia
    loader.create_views(settings, contract, con)
    assert scalar(con, "SELECT count(*) FROM raw_municipal_teste.pessoas") == 2
    again = _capture_of(con, settings, "pessoas", "http://x/p", "codigo,nome\n1,Ana\n3,Caio\n", "p2")
    loader.load_capture(con, settings, contract, again)
    loader.create_views(settings, contract, con)
    assert (
        scalar(con, "SELECT count(*) FROM raw_municipal_teste.pessoas") == 2
    )  # a captura nova substitui a velha


def test_a_column_that_comes_entirely_empty_still_exists_in_the_view(
    con: Connection, settings: Settings, tmp_path: Path
) -> None:
    contract = make_contract(tmp_path)
    _capture_of(con, settings, "pessoas", "http://x/p", "codigo,nome\n1,\n2,\n", "e1")
    loader.load_pending(con, settings, contract)
    assert rows(con, "SELECT nome FROM raw_municipal_teste.pessoas") == [{"nome": None}, {"nome": None}]


def test_merge_keeps_the_latest_capture_of_each_key_across_files_and_the_first_row_within_one(
    con: Connection, settings: Settings, tmp_path: Path
) -> None:
    contract = make_contract(tmp_path)
    a = _capture_of(con, settings, "pessoas", "http://x/a", "codigo,nome\n1,Ana\n2,Bia\n1,Outra\n", "m1")
    b = _capture_of(con, settings, "pessoas", "http://x/b", "codigo,nome\n2,Bea\n3,Caio\n", "m2")
    loader.load_pending(con, settings, contract)
    assert rows(
        con, "SELECT codigo, nome, _source_file_id FROM raw_municipal_teste.pessoas ORDER BY codigo"
    ) == [
        {"codigo": "1", "nome": "Ana", "_source_file_id": a["id_captura"]},
        {"codigo": "2", "nome": "Bea", "_source_file_id": b["id_captura"]},
        {"codigo": "3", "nome": "Caio", "_source_file_id": b["id_captura"]},
    ]


def test_the_raw_folder_holds_only_the_current_captures(
    con: Connection, settings: Settings, tmp_path: Path
) -> None:
    contract = make_contract(tmp_path)
    old = _capture_of(con, settings, "pessoas", "http://x/p", "codigo,nome\n1,Ana\n", "v1")
    loader.load_pending(con, settings, contract)
    folder = loader.raw_dir(settings, contract) / "pessoas"
    assert [d.name for d in folder.iterdir()] == [str(old["id_captura"])]
    new = _capture_of(con, settings, "pessoas", "http://x/p", "codigo,nome\n1,Ana\n2,Bia\n", "v2")
    loader.load_pending(con, settings, contract)
    assert [d.name for d in folder.iterdir()] == [str(new["id_captura"])]  # a substituída saiu
    (folder / "999").mkdir()  # sobra de uma captura que o landing não tem como vigente
    (folder / "999" / "x.parquet").write_bytes(b"")
    loader.load_pending(con, settings, contract)
    assert [d.name for d in folder.iterdir()] == [str(new["id_captura"])]
    assert (loader.raw_dir(settings, contract) / "_dlt_loads").is_dir()  # as tabelas internas do dlt ficam


def test_a_failed_load_keeps_the_previous_capture_until_the_new_one_enters(
    monkeypatch: pytest.MonkeyPatch, con: Connection, settings: Settings, tmp_path: Path
) -> None:
    contract = make_contract(tmp_path)
    _capture_of(con, settings, "pessoas", "http://x/p", "codigo,nome\n1,Ana\n", "w1")
    loader.load_pending(con, settings, contract)
    _capture_of(con, settings, "pessoas", "http://x/p", "codigo,nome\n1,Ana\n2,Bia\n", "w2")
    monkeypatch.setattr(loader, "load_file", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("falha")))
    loader.load_pending(con, settings, contract)
    assert scalar(con, "SELECT count(*) FROM raw_municipal_teste.pessoas") == 1  # o dado antigo continua
    monkeypatch.undo()
    loader.load_pending(con, settings, contract)
    assert scalar(con, "SELECT count(*) FROM raw_municipal_teste.pessoas") == 2


def test_a_leftover_of_an_interrupted_load_of_the_same_capture_does_not_duplicate(
    con: Connection, settings: Settings, tmp_path: Path
) -> None:
    contract = make_contract(tmp_path)
    capture = _capture_of(con, settings, "retratos", "http://x/r", "codigo,valor\n1,10\n", "i1")
    loader.load_capture(con, settings, contract, capture)
    con.execute("UPDATE metadata.capturas SET dt_carga = NULL")  # a carga caiu depois de gravar o Parquet
    loader.load_pending(con, settings, contract)
    assert scalar(con, "SELECT count(*) FROM raw_municipal_teste.retratos") == 1


def test_a_native_table_of_the_previous_raw_stays_until_the_rebuild_turns_it_into_a_view(
    con: Connection, settings: Settings, tmp_path: Path
) -> None:
    contract = make_contract(tmp_path)
    capture = _capture_of(con, settings, "pessoas", "http://x/p", "codigo,nome\n1,Ana\n", "n1")
    con.execute("CREATE SCHEMA raw_municipal_teste")
    con.execute("CREATE TABLE raw_municipal_teste.pessoas AS SELECT '9' AS codigo, 'Antiga' AS nome")
    messages: list[str] = []
    loader.create_views(settings, contract, con, messages.append)
    assert any("tabela nativa" in m for m in messages)
    assert scalar(con, "SELECT nome FROM raw_municipal_teste.pessoas") == "Antiga"
    loader.load_pending(con, settings, contract, rebuild=True)
    assert rows(con, "SELECT codigo, _source_file_id FROM raw_municipal_teste.pessoas") == [
        {"codigo": "1", "_source_file_id": capture["id_captura"]}
    ]
    assert scalar(con, "SELECT count(*) FROM duckdb_views() WHERE view_name = 'pessoas'") == 1


def test_a_table_without_the_column_the_new_key_needs_is_reloaded_instead_of_failing(
    con: Connection, settings: Settings, tmp_path: Path
) -> None:
    old = make_contract(tmp_path)
    capture = _capture_of(con, settings, "pessoas", "http://x/p", "codigo,nome\n1,Ana\n1,Ana\n2,Bia\n", "k1")
    loader.load_pending(con, settings, old, only_dataset="pessoas")
    file = tmp_path / "contract.yml"  # a chave da tabela já carregada passa a ser o conteúdo da linha
    file.write_text(
        file.read_text(encoding="utf-8").replace("primary_key: [codigo]", "primary_key: [_row_hash]")
    )
    new = load_contract(file)
    messages: list[str] = []
    loader.load_pending(con, settings, new, only_dataset="pessoas", log=messages.append)
    assert rows(con, "SELECT codigo, _source_file_id FROM raw_municipal_teste.pessoas ORDER BY 1") == [
        {"codigo": "1", "_source_file_id": capture["id_captura"]},
        {"codigo": "1", "_source_file_id": capture["id_captura"]},
        {"codigo": "2", "_source_file_id": capture["id_captura"]},
    ]  # recarregada do landing: as linhas idênticas da fonte ficam todas
    assert any("recarreg" in m for m in messages)
    logged = rows(
        con,
        "SELECT resultado, detalhe FROM metadata.fontes_verificacoes WHERE verificacao = 'recarga_por_chave'",
    )
    assert len(logged) == 1 and "_row_hash" in logged[0]["detalhe"]
    loader.load_pending(con, settings, new, only_dataset="pessoas")  # a seguinte não recarrega de novo
    assert scalar(con, "SELECT count(*) FROM raw_municipal_teste.pessoas") == 3
    assert (
        scalar(
            con, "SELECT count(*) FROM metadata.fontes_verificacoes WHERE verificacao = 'recarga_por_chave'"
        )
        == 1
    )


def test_a_dataset_that_fails_to_load_is_recorded_and_the_others_still_load(
    monkeypatch: pytest.MonkeyPatch, con: Connection, settings: Settings, tmp_path: Path
) -> None:
    contract = make_contract(tmp_path)
    _capture_of(con, settings, "pessoas", "http://x/p", "codigo,nome\n1,Ana\n", "f1")
    _capture_of(con, settings, "fixos", "http://x/f", "codigo\n7\n", "f2")
    real = loader.load_file

    def flaky(settings: Settings, contract: SourceContract, dataset: Any, *args: Any, **kwargs: Any) -> Any:
        if dataset.name == "pessoas":
            raise RuntimeError("esquema incompatível")
        return real(settings, contract, dataset, *args, **kwargs)

    monkeypatch.setattr(loader, "load_file", flaky)
    captures, _ = loader.load_pending(con, settings, contract)
    assert captures == 1 and scalar(con, "SELECT count(*) FROM raw_municipal_teste.fixos") == 1
    status, details = monitoring.latest_status(con, "teste", "pessoas")
    assert status == "error" and "esquema incompatível" in details[0]
    assert scalar(con, "SELECT count(*) FROM metadata.capturas WHERE dt_carga IS NULL") == 1  # tenta de novo
    monkeypatch.undo()
    assert loader.load_pending(con, settings, contract)[0] == 1  # a próxima carga recupera
    assert monitoring.latest_status(con, "teste", "pessoas")[0] == "ok"


def _serving(versions: list[bytes]) -> Any:
    """Downloader que serve, a cada chamada, a próxima versão do arquivo (a fonte mudando e voltando)."""
    calls = iter(versions)

    def download(url: str, folder: Path) -> tuple[Path, str, int]:
        content = next(calls)
        digest = hashlib.sha256(content).hexdigest()
        folder.mkdir(parents=True, exist_ok=True)
        file = folder / f"deputados-{digest[:12]}.csv"
        file.write_bytes(content)
        return file, digest, len(content)

    return download


def test_a_source_that_goes_back_to_an_old_content_becomes_a_new_capture_and_the_raw_follows(
    con: Connection, settings: Settings, contract: SourceContract, tmp_path: Path
) -> None:
    original = synthetic_files(tmp_path / "origin")[contract.url("deputados")].read_bytes()
    a, b = original, original + b"\n"
    download = _serving([a, b, a, a])
    ids = [
        landing.extract(con, settings, contract, "deputados", downloader=download, head_request=no_headers)
        for _ in range(4)
    ]
    assert len(set(ids[:3])) == 3  # A, B e a volta a A são três capturas, o histórico não é reescrito
    assert ids[3] == ids[2]  # o ciclo seguinte (ainda A) não cria outra
    current = landing.current_captures(con, contract.source)
    assert [(c["id_captura"], c["sha256"]) for c in current] == [(ids[2], hashlib.sha256(a).hexdigest())]
    assert current[0]["dt_carga"] is None  # ainda não carregada: o loader a carrega e o raw volta a A
    assert scalar(con, "SELECT count(*) FROM metadata.capturas") == 3


def test_rows_whose_values_only_shift_between_columns_are_different_rows(tmp_path: Path) -> None:
    contract = make_contract(tmp_path)
    dataset = contract.datasets["lancamentos"]
    file = tmp_path / "lancamentos.csv"
    file.write_text("codigo,valor\nab,c\na,bc\nx,\n,x\n", encoding="utf-8")
    hashes = [r["_row_hash"].split(":")[0] for r in loader.read_rows(file, contract, dataset, 1, Counter())]
    assert len(set(hashes)) == len(hashes) == 4


def test_the_landing_clock_is_brasilia_not_utc_at_the_turn_of_the_year(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Utc2027(datetime):
        @classmethod
        def now(cls, tz: Any = None) -> "Utc2027":  # 22h30 de 31/12/2026 em Brasília
            return cls(2027, 1, 1, 1, 30, tzinfo=UTC).astimezone(tz)

    monkeypatch.setattr(runs, "datetime", Utc2027)
    assert landing.current_year() == 2026
