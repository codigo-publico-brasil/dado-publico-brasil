"""Landing (arquivos intactos com hash) e raw (carga fiel pelo dlt)."""

from pathlib import Path

import duckdb
from synthetic_camara import fake_downloader, no_headers, synthetic_files

from dado_publico_brasil.core.settings import Settings
from dado_publico_brasil.core.warehouse import Connection, columns, scalar, tables
from dado_publico_brasil.ingestion import landing, loader
from dado_publico_brasil.ingestion.contract import SourceContract, load_contract


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
        "SELECT path, sha256, run_id FROM metadata.captures WHERE id = ?", (capture_id,)
    ).fetchone() or ("", "", 0)
    assert path.startswith("landing/camara/deputados-")
    assert sha[:12] in path
    assert (settings.storage_root / path).exists()
    assert con.execute("SELECT stage, status FROM metadata.runs WHERE id = ?", (run_id,)).fetchone() == (
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
    assert scalar(con, "SELECT COUNT(*) FROM metadata.captures") == 1


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
    assert [c["id"] for c in landing.current_captures(con, "camara")] == [latest]


def test_raw_has_only_allowed_columns_and_never_the_personal_document(
    raw: tuple[Connection, Settings],
) -> None:
    con, _ = raw
    cols = set(columns(con, "raw_federal_camara", "deputados"))
    assert "cpf" not in cols
    assert {"uri", "nome", "nome_civil", "_source_file_id"} <= cols
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
            "WHERE NOT EXISTS (SELECT 1 FROM metadata.captures c WHERE c.id = t._source_file_id)",
        )
        assert orphans == 0, table


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


def test_load_marks_the_capture_as_loaded(raw: tuple[Connection, Settings]) -> None:
    con, _ = raw
    assert scalar(con, "SELECT COUNT(*) FROM metadata.captures WHERE loaded_at IS NULL") == 0


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
    settings: Settings, contract: SourceContract, dataset: str, text: str, file_id: int
) -> dict[str, int]:
    file = settings.storage_root / f"{dataset}-{file_id}.csv"
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(text, encoding="utf-8")
    return loader.load_file(settings, contract, contract.datasets[dataset], file, file_id)


def test_new_source_enters_with_only_a_contract_and_rejects_rows_without_key(
    tmp_path: Path,
) -> None:
    settings = Settings(storage_root=tmp_path / "store")
    contract = make_contract(tmp_path)
    stats = load(settings, contract, "pessoas", "codigo,nome,cpf\n1,Ana,111\n2,Bia,222\n,Sem Chave,333\n", 7)
    assert stats == {"read": 3, "filtered": 0, "loaded": 2, "rejected": 1, "conflicting": 0}
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
    load(settings, contract, "fixos", "codigo\n3\n", 2)
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


def test_the_load_registers_one_balance_that_is_an_error_for_collisions_and_rejections_and_ok_otherwise(
    con: Connection,
) -> None:
    from dado_publico_brasil.ingestion import monitoring

    monitoring.check_load(
        con, "teste", "ds", 2006, {"read": 10, "filtered": 3, "loaded": 6, "rejected": 1, "conflicting": 2}
    )
    found = con.execute("SELECT check_name, status, detail FROM metadata.source_checks").fetchall()
    assert [(c, s) for c, s, _ in found] == [("carga", "error")]
    assert "filtradas pelo only 3" in found[0][2] and "colisões de chave 2" in found[0][2]
    monitoring.check_load(
        con, "teste", "limpo", None, {"read": 5, "filtered": 0, "loaded": 5, "rejected": 0, "conflicting": 0}
    )
    assert scalar(con, "SELECT status FROM metadata.source_checks WHERE dataset = 'limpo'") == "ok"
