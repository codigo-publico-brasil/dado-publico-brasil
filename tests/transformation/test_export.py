"""Export do lake público (ADR 0035): Parquet fiel ao warehouse, idempotente, com catálogo e descrições.

Usa um warehouse pequeno montado aqui (rápido); o destino é a pasta local, o mesmo código do R2 menos o
segredo. O que depende de credencial real (COPY, LIST e DELETE em `r2://` e o PUT do catálogo) não é testado aqui.
"""

import hashlib
import json
import logging
import mimetypes
import re
import shutil
import zipfile
from datetime import UTC, datetime
from pathlib import Path

import duckdb
import pytest

from dado_publico_brasil.core import runs, s3, warehouse
from dado_publico_brasil.core.settings import Settings
from dado_publico_brasil.core.warehouse import Connection, scalar
from dado_publico_brasil.ingestion import arquivos, landing
from dado_publico_brasil.ingestion import contract as contracts
from dado_publico_brasil.transformation import colecoes, dbt, export, lake, observability, tables, verify

MODELS = {
    "nodes": {
        "model.x.fct_votos": {
            "resource_type": "model",
            "name": "fct_votos",
            "original_file_path": "models\\marts\\legislativo\\fct_votos.sql",
            "config": {"meta": {"particao": "year(dt_voto)"}},
        }
    }
}
VOTOS = "marts/legislativo/fct_votos"


def build(con: Connection, settings: Settings) -> None:
    for schema in ("staging", "intermediate", "marts", "raw_x", "identity"):
        con.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")
    con.execute(
        "CREATE TABLE marts.fct_votos AS SELECT i AS id_voto, DATE '2020-06-01' + to_days(365 * (i % 3)::INTEGER) AS dt_voto, "
        "'x' || i AS cpf_votante, i * 2 AS qtd FROM range(1000) t(i)"
    )
    con.execute("COMMENT ON TABLE marts.fct_votos IS 'Votos de teste.'")
    con.execute("COMMENT ON COLUMN marts.fct_votos.qtd IS 'Quantidade de teste.'")
    con.execute("CREATE TABLE intermediate.int_x AS SELECT 1 AS a")
    con.execute(
        "CREATE TABLE staging.stg_camara__base AS SELECT i AS id, 'n' || i AS nome FROM range(50) t(i)"
    )
    con.execute(
        "CREATE VIEW staging.stg_camara__visao AS SELECT id, upper(nome) AS nome FROM staging.stg_camara__base"
    )
    con.execute("CREATE TABLE staging.stg_tse__x AS SELECT 1 AS a")
    con.execute("CREATE TABLE staging.stg_identity__y AS SELECT 1 AS a")
    con.execute("CREATE TABLE staging.stg_metadata__z AS SELECT 1 AS a")
    con.execute("CREATE TABLE raw_x.segredo AS SELECT 1 AS a")
    target = settings.state_dir / "dbt" / "target"
    target.mkdir(parents=True, exist_ok=True)
    (target / "manifest.json").write_text(json.dumps(MODELS), encoding="utf-8")


def run(
    con: Connection, settings: Settings, max_bytes: int = tables.MAX_BYTES
) -> tuple[Path, dict[str, int]]:
    build(con, settings)
    con.close()  # o export abre o warehouse só para leitura
    result = export.export(settings, max_bytes=max_bytes)
    return settings.storage_root / "lake", result


def change(settings: Settings, sql: str) -> None:
    live = warehouse.connect(settings)
    live.execute(sql)
    live.close()


def manifest(out: Path) -> dict[str, list[dict[str, object]]]:
    return json.loads((out / "manifesto.json").read_text(encoding="utf-8"))  # type: ignore[no-any-return]


SNAPSHOT = lake.snapshot


@pytest.fixture(autouse=True)
def _no_monthly_version(monkeypatch: pytest.MonkeyPatch) -> None:
    """A versão do mês prende os arquivos da primeira execução; os testes de órfãos partem sem ela."""
    monkeypatch.setattr(lake, "snapshot", lambda *a: None)


def where(out: Path, key: str) -> Path:
    """O (primeiro) arquivo que o manifesto publicado dá à tabela de caminho `key`."""
    entry = next(t for t in manifest(out)["tabelas"] if t["caminho"] == key)
    return out / entry["arquivos"][0]["arquivo"]  # type: ignore[no-any-return,index]


def plain(path: str) -> str:
    """O caminho sem o segmento da execução (`<key>/<id>/<nome>.parquet` vira `<key>.parquet`)."""
    path = re.sub(r"/\d{8}T\d{6}Z(?:-\d+)?/ano=", "/ano=", path)
    return re.sub(r"/\d{8}T\d{6}Z(?:-\d+)?/[^/]+\.parquet$", ".parquet", path)


def votos(out: Path) -> dict[str, object]:
    return [t for t in manifest(out)["tabelas"] if t["tabela"] == "fct_votos"][0]


def test_every_table_is_exported_with_the_same_rows_and_schema(con: Connection, settings: Settings) -> None:
    out, result = run(con, settings)
    tables = manifest(out)["tabelas"]
    assert {(t["camada"], t["tabela"], t["caminho"], t["camada_medalhao"]) for t in tables} == {
        ("marts", "fct_votos", VOTOS, "ouro"),
        ("intermediate", "int_x", "intermediate/int_x", "prata"),
        ("staging", "stg_camara__base", "staging/legislativo/federal/camara/stg_camara__base", "prata"),
        ("staging", "stg_camara__visao", "staging/legislativo/federal/camara/stg_camara__visao", "prata"),
        ("staging", "stg_tse__x", "staging/judiciario/federal/tse/stg_tse__x", "prata"),
        ("metadata", "capturas", "metadata/capturas", "bronze"),
        ("metadata", "fontes_verificacoes", "metadata/fontes_verificacoes", "bronze"),
        ("metadata", "testes_resultados", "metadata/testes_resultados", "bronze"),
    }
    assert result["tabelas"] == len(tables) and result["gravadas"] == len(tables)
    live = warehouse.connect(settings, read_only=True)
    for t in tables:
        cols = [c["nome"] for c in t["colunas"]]  # type: ignore[attr-defined]
        for f in t["arquivos"]:  # type: ignore[attr-defined]
            assert (out / f["arquivo"]).stat().st_size == f["bytes"]
        file = (out / t["arquivos"][0]["arquivo"]).as_posix()  # type: ignore[index]
        expected = scalar(live, f'SELECT count(*) FROM {t["camada"]}."{t["tabela"]}"')
        assert scalar(live, f"SELECT count(*) FROM read_parquet('{file}')") == t["linhas"] == expected
        got = [r[0] for r in live.execute(f"DESCRIBE SELECT * FROM read_parquet('{file}')").fetchall()]
        assert got == cols
    live.close()


def test_a_second_export_without_changes_rewrites_nothing(con: Connection, settings: Settings) -> None:
    out, first = run(con, settings)
    stamps = {p: p.stat().st_mtime_ns for p in out.rglob("*.parquet")}
    second = export.export(settings)
    assert second["gravadas"] == 0 and second["ignoradas"] == first["tabelas"] and second["bytes"] == 0
    assert {p: p.stat().st_mtime_ns for p in out.rglob("*.parquet")} == stamps
    assert verify.verify(settings) == []


def test_an_unchanged_run_writes_and_sends_nothing_and_prints_progress(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture, con: Connection, settings: Settings
) -> None:
    out, _ = run(con, settings)
    stamps = {p: p.stat().st_mtime_ns for p in out.iterdir() if p.is_file()}
    text = (out / "manifesto.json").read_text(encoding="utf-8")
    tables = len(manifest(out)["tabelas"])
    caplog.clear()
    caplog.set_level(logging.INFO)
    sent: list[str] = []
    monkeypatch.setattr(shutil, "copyfile", lambda s, d: sent.append(str(d)))
    export.export(settings)
    shown = caplog.text
    assert sent == [] and (out / "manifesto.json").read_text(encoding="utf-8") == text
    assert {p: p.stat().st_mtime_ns for p in out.iterdir() if p.is_file()} == stamps
    for phase in ("impressões digitais", "escrita", "arquivos", "catálogo e manifesto", "órfãos"):
        assert f"[{phase}] " in shown
    assert shown.count(": ignorada (") == tables and ": gravada" not in shown


def test_a_changed_table_prints_as_written_and_the_rest_as_ignored(
    caplog: pytest.LogCaptureFixture, con: Connection, settings: Settings
) -> None:
    out, _ = run(con, settings)
    tables = len(manifest(out)["tabelas"])
    change(settings, "INSERT INTO intermediate.int_x VALUES (2)")
    caplog.clear()
    caplog.set_level(logging.INFO)
    export.export(settings)
    lines = [ln for ln in caplog.messages if ": gravada (" in ln or ": ignorada (" in ln]
    assert [ln.split(":")[0].strip() for ln in lines if ": gravada (" in ln] == ["intermediate.int_x"]
    assert len(lines) == tables


def test_a_new_table_is_added_and_a_removed_one_needs_prune(con: Connection, settings: Settings) -> None:
    out, first = run(con, settings)
    change(settings, "CREATE TABLE intermediate.int_nova AS SELECT 1 AS a")
    again = export.export(settings)
    assert again["gravadas"] == 1 and again["tabelas"] == first["tabelas"] + 1
    assert where(out, "intermediate/int_nova").exists()
    nova = where(out, "intermediate/int_nova")
    change(settings, "DROP TABLE intermediate.int_nova")
    export.export(settings, prune=True)
    assert not nova.exists() and verify.verify(settings) == []


def test_a_description_change_alone_replaces_the_catalog_and_the_manifest(
    con: Connection, settings: Settings
) -> None:
    out, _ = run(con, settings)
    change(settings, "COMMENT ON TABLE intermediate.int_x IS 'Outra descricao.'")
    assert export.export(settings)["gravadas"] == 1
    cat = duckdb.connect(str(out / "catalogo.duckdb"), read_only=True)
    assert scalar(cat, "SELECT comment FROM duckdb_views() WHERE view_name = 'int_x'") == "Outra descricao."
    cat.close()


def test_changing_the_public_base_url_replaces_the_catalog_and_the_manifest(
    con: Connection, settings: Settings
) -> None:
    out, _ = run(con, settings)
    one, two = out.as_posix(), f"{out.as_posix()}/../lake"  # as duas resolvem para os mesmos arquivos
    export.export(settings, base_url=one)
    export.export(settings, base_url=one)
    stamp = (out / "catalogo.duckdb").stat().st_mtime_ns
    export.export(settings, base_url=two)
    assert manifest(out)["base"] == two  # type: ignore[comparison-overlap]
    assert (out / "catalogo.duckdb").stat().st_mtime_ns != stamp
    cat = duckdb.connect(str(out / "catalogo.duckdb"), read_only=True)
    assert f"{two}/" in scalar(cat, "SELECT sql FROM duckdb_views() WHERE view_name = 'int_x'")
    cat.close()


def test_a_table_that_changed_path_leaves_no_orphan_even_without_prune(
    con: Connection, settings: Settings
) -> None:
    out, _ = run(con, settings)
    old = where(out, VOTOS)
    moved = json.loads(json.dumps(MODELS).replace("legislativo", "outro"))
    (settings.state_dir / "dbt" / "target" / "manifest.json").write_text(json.dumps(moved), encoding="utf-8")
    export.export(settings)
    assert not old.exists() and where(out, "marts/outro/fct_votos").exists()
    assert verify.verify(settings) == []


def test_the_time_of_each_table_is_kept_for_the_next_look(con: Connection, settings: Settings) -> None:
    run(con, settings)
    tempos = json.loads((settings.state_dir / "export_tempos.json").read_text(encoding="utf-8"))
    assert tempos["marts.fct_votos"].keys() == {"impressao_s", "escrita_s", "resultado"}
    assert tempos["marts.fct_votos"]["resultado"] == "gravada"
    assert export.export(settings)["ignoradas"] == len(tempos)
    again = json.loads((settings.state_dir / "export_tempos.json").read_text(encoding="utf-8"))
    assert {v["resultado"] for v in again.values()} == {"ignorada"}


def test_a_changed_table_alone_is_rewritten_and_verify_catches_tampering(
    con: Connection, settings: Settings
) -> None:
    out, _ = run(con, settings)
    change(settings, "INSERT INTO staging.stg_camara__base VALUES (999, 'novo')")
    assert export.export(settings)["gravadas"] == 2  # a tabela e a view que a lê
    file = where(out, VOTOS)
    file.write_bytes(b"adulterado")
    assert verify.verify(settings) == [f"{file.relative_to(out).as_posix()} difere do manifesto"]


def test_the_catalog_attaches_read_only_and_queries_with_descriptions(
    con: Connection, settings: Settings
) -> None:
    out, _ = run(con, settings)
    cat = duckdb.connect(str(out / "catalogo.duckdb"), read_only=True)
    for t in manifest(out)["tabelas"]:
        assert scalar(cat, f'SELECT count(*) FROM {t["camada"]}."{t["tabela"]}"') == t["linhas"]
    assert (
        scalar(cat, "SELECT comment FROM duckdb_views() WHERE view_name = 'fct_votos'") == "Votos de teste."
    )
    assert (
        scalar(cat, "SELECT comment FROM duckdb_columns() WHERE column_name = 'qtd'")
        == "Quantidade de teste."
    )
    assert scalar(cat, "SELECT versao_commit IS NOT NULL FROM metadata.exportacao")
    assert (
        scalar(
            cat,
            "SELECT count(*) FROM duckdb_columns() WHERE schema_name = 'metadata' AND table_name = 'exportacao' "
            "AND coalesce(comment, '') = ''",
        )
        == 0
    )  # as 3 colunas da exportação também são descritas (issue 197)
    cat.close()


def test_no_personal_column_and_no_private_layer_is_exported(con: Connection, settings: Settings) -> None:
    out, _ = run(con, settings)
    tables = manifest(out)["tabelas"]
    names = [c["nome"] for t in tables for c in t["colunas"]]  # type: ignore[attr-defined]
    assert "cpf_votante" not in names and "id_voto" in names
    assert {t["camada"] for t in tables}.isdisjoint({"raw_x", "identity", "elementary", "main"})
    assert not [t for t in tables if str(t["tabela"]).startswith(("stg_identity", "stg_metadata"))]


def test_a_big_table_with_a_partition_is_split_by_year_and_filters_by_it(
    con: Connection, settings: Settings
) -> None:
    out, _ = run(con, settings, max_bytes=1)
    split = votos(out)
    names = sorted(f["arquivo"] for f in split["arquivos"])  # type: ignore[attr-defined]
    assert [plain(n) for n in names] == [f"{VOTOS}/ano={y}/part-0.parquet" for y in (2020, 2021, 2022)]
    assert split["particao"] == "year(dt_voto)" and split["ano"] == [2020, 2021, 2022]
    assert split["colunas"][-1]["nome"] == "ano"  # type: ignore[index]
    assert sum(f["linhas"] for f in split["arquivos"]) == 1000  # type: ignore[attr-defined]
    assert verify.verify(settings) == []
    cat = duckdb.connect(str(out / "catalogo.duckdb"), read_only=True)
    live = warehouse.connect(settings, read_only=True)
    ids = "SELECT id_voto FROM marts.fct_votos ORDER BY 1"
    assert cat.execute(ids).fetchall() == live.execute(ids).fetchall()
    glob = f"{(out / VOTOS).as_posix()}/**/*.parquet"
    got = scalar(
        cat, f"SELECT count(*) FROM read_parquet('{glob}', hive_partitioning = true) WHERE ano = 2021"
    )
    assert got == scalar(live, "SELECT count(*) FROM marts.fct_votos WHERE year(dt_voto) = 2021") > 0
    cat.close()
    live.close()


def test_a_small_table_with_a_partition_is_one_file_sorted_by_the_period(
    con: Connection, settings: Settings
) -> None:
    out, _ = run(con, settings)
    split = votos(out)
    assert [plain(f["arquivo"]) for f in split["arquivos"]] == [f"{VOTOS}.parquet"]  # type: ignore[attr-defined]
    assert split["particao"] == "year(dt_voto)" and split["ano"] is None
    mem = duckdb.connect()
    years = [
        r[0] for r in mem.execute(f"SELECT year(dt_voto) FROM '{where(out, VOTOS).as_posix()}'").fetchall()
    ]
    assert years == sorted(years)


def test_a_null_year_fails_with_a_clear_message(con: Connection, settings: Settings) -> None:
    build(con, settings)
    con.execute("INSERT INTO marts.fct_votos VALUES (5000, NULL, 'x', 1)")
    con.close()
    with pytest.raises(ValueError, match="ano nulo"):
        export.export(settings, max_bytes=1)


def test_switching_layout_or_dropping_a_table_removes_the_orphans(
    con: Connection, settings: Settings
) -> None:
    out, _ = run(con, settings)
    single = where(out, VOTOS)
    change(settings, "INSERT INTO marts.fct_votos VALUES (5000, DATE '2021-01-01', 'x', 1)")
    result = export.export(settings, max_bytes=1)  # de arquivo único para partição
    assert result["orfaos"] == 1 and not single.exists()
    change(settings, "INSERT INTO marts.fct_votos VALUES (5001, DATE '2021-01-01', 'x', 1)")
    change(settings, "DROP VIEW staging.stg_camara__visao")
    result = export.export(settings, prune=True)  # de partição para arquivo único, e uma tabela removida
    assert result["orfaos"] == 3 + 1
    listed = {p.relative_to(out).as_posix() for p in out.rglob("*.parquet")}
    assert listed == {f["arquivo"] for t in manifest(out)["tabelas"] for f in t["arquivos"]}  # type: ignore[attr-defined]
    assert verify.verify(settings) == []


def test_a_table_missing_from_the_warehouse_blocks_the_export_unless_pruned(
    con: Connection, settings: Settings
) -> None:
    out, _ = run(con, settings)
    before = sorted(p.as_posix() for p in out.rglob("*") if p.is_file())
    change(settings, "DROP TABLE intermediate.int_x")
    with pytest.raises(ValueError, match="intermediate.int_x.*--prune"):
        export.export(settings)
    assert sorted(p.as_posix() for p in out.rglob("*") if p.is_file()) == before  # nada apagado nem publicado
    assert export.export(settings, prune=True)["orfaos"] == 1


def test_duplicate_row_pairs_change_the_fingerprint(con: Connection, settings: Settings) -> None:
    build(con, settings)
    con.execute("CREATE TABLE intermediate.int_dup AS SELECT i AS a FROM range(5) t(i)")
    con.close()
    out = settings.storage_root / "lake"
    export.export(settings)
    change(
        settings, "INSERT INTO intermediate.int_dup VALUES (1), (1)"
    )  # o xor das duas linhas iguais se cancela
    result = export.export(settings)
    assert result["gravadas"] == 1
    assert [t["linhas"] for t in manifest(out)["tabelas"] if t["tabela"] == "int_dup"] == [7]


def kv(file: Path) -> dict[str, str]:
    rows = (
        duckdb.connect()
        .execute("SELECT key, value FROM parquet_kv_metadata(?)", [file.as_posix()])
        .fetchall()
    )
    return {k.decode(): v.decode() for k, v in rows}


@pytest.mark.parametrize("max_bytes", [tables.MAX_BYTES, 1])
def test_the_parquet_carries_the_table_and_column_descriptions(
    con: Connection, settings: Settings, max_bytes: int
) -> None:
    out, _ = run(con, settings, max_bytes=max_bytes)
    live = warehouse.connect(settings, read_only=True)
    comments = dict(
        live.execute(
            "SELECT column_name, comment FROM duckdb_columns() WHERE schema_name = 'marts' "
            "AND table_name = 'fct_votos' AND comment IS NOT NULL"
        ).fetchall()
    )
    live.close()
    for f in votos(out)["arquivos"]:  # type: ignore[attr-defined]
        meta = kv(out / f["arquivo"])
        assert meta["descricao"] == "Votos de teste."
        described = json.loads(meta["descricoes_colunas"])
        assert described["qtd"] == comments["qtd"] == "Quantidade de teste."
        assert "cpf_votante" not in described and set(described) <= {"id_voto", "dt_voto", "qtd", "ano"}
        assert meta["id_execucao"]  # os metadados de antes continuam


def test_a_changed_description_rewrites_the_table(con: Connection, settings: Settings) -> None:
    out, _ = run(con, settings)
    change(settings, "COMMENT ON COLUMN marts.fct_votos.qtd IS 'Outra descrição.'")
    assert export.export(settings)["gravadas"] == 1
    meta = kv(where(out, VOTOS))
    assert json.loads(meta["descricoes_colunas"])["qtd"] == "Outra descrição."


def test_the_manifest_carries_the_licence_declared_by_the_source(con: Connection, settings: Settings) -> None:
    out, _ = run(con, settings)
    found = {t["tabela"]: t["licenca"] for t in manifest(out)["tabelas"]}
    assert found["stg_tse__x"] == "CC BY"
    assert found["stg_camara__base"] is None and found["fct_votos"] is None  # sem licença registrada / mart


def test_huge_descriptions_are_cut_with_a_warning(con: Connection, settings: Settings) -> None:
    build(con, settings)
    con.execute(f"COMMENT ON COLUMN marts.fct_votos.qtd IS '{'x' * (tables.MAX_KV_BYTES + 10)}'")
    con.close()
    with pytest.warns(UserWarning, match="descricoes_colunas"):
        export.export(settings)
    meta = kv(where(settings.storage_root / "lake", VOTOS))
    assert len(meta["descricoes_colunas"].encode()) <= tables.MAX_KV_BYTES


def write_models(settings: Settings, particao: str) -> None:
    node = json.loads(json.dumps(MODELS))["nodes"]["model.x.fct_votos"]
    node["config"]["meta"]["particao"] = particao
    (settings.state_dir / "dbt" / "target" / "manifest.json").write_text(
        json.dumps({"nodes": {"model.x.fct_votos": node}}), encoding="utf-8"
    )


def test_a_column_already_named_year_is_the_partition_or_a_clear_error(
    con: Connection, settings: Settings
) -> None:
    build(con, settings)
    con.execute("ALTER TABLE marts.fct_votos ADD COLUMN ano INTEGER")
    con.execute("UPDATE marts.fct_votos SET ano = year(dt_voto)")
    con.close()
    write_models(settings, "year(dt_voto)")
    with pytest.raises(ValueError, match="já tem uma coluna `ano`"):
        export.export(settings, max_bytes=1)
    write_models(settings, "ano")
    export.export(settings, max_bytes=1)
    split = [t for t in manifest(settings.storage_root / "lake")["tabelas"] if t["tabela"] == "fct_votos"][0]
    assert split["ano"] == [2020, 2021, 2022]
    assert [c["nome"] for c in split["colunas"]].count("ano") == 1  # type: ignore[attr-defined]


def test_a_mart_without_the_dbt_manifest_takes_its_folder_from_the_models_tree() -> None:
    assert tables.domain({}, "dim_pessoas") == "pessoas"


def test_publish_docs_uploads_both_pages_as_html_and_does_nothing_without_r2(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, settings: Settings
) -> None:
    sent: list[tuple[str, str | None]] = []
    page = tmp_path / "p.html"
    page.write_text("<html></html>")
    monkeypatch.setattr(dbt, "static_docs", lambda s: page)
    monkeypatch.setattr(observability, "html_report", lambda s: page)
    monkeypatch.setattr(
        lake, "request", lambda m, key, path=None, content_type=None: sent.append((key, content_type))
    )
    monkeypatch.setattr(lake, "index", lambda s: page)
    monkeypatch.setattr(lake, "situation", lambda s, limits=None: page)
    monkeypatch.setattr(lake, "r2", lambda: {})
    assert lake.publish_docs(settings) == [] and sent == []
    monkeypatch.setattr(lake, "r2", lambda: {"BUCKET": "b"})
    assert lake.publish_docs(settings) == [
        "docs/dbt.html",
        "docs/qualidade.html",
        "docs/situacao.html",
        "docs/index.html",
    ]
    assert sent == [
        ("docs/dbt.html", "text/html; charset=utf-8"),
        ("docs/qualidade.html", "text/html; charset=utf-8"),
        ("docs/situacao.html", "text/html; charset=utf-8"),
        ("docs/index.html", "text/html; charset=utf-8"),
    ]


def test_the_home_page_fills_the_card_from_the_published_manifest(
    con: Connection, settings: Settings
) -> None:
    out, _ = run(con, settings)
    html = lake.index(settings).read_text(encoding="utf-8")
    published = manifest(out)
    assert "{{" not in html
    assert str(published["id_execucao"]) in html and f">{len(published['tabelas'])}<" in html


def test_seed_mart_goes_to_the_reference_folder() -> None:
    assert tables.table_path({}, "marts", "dim_cargos") == "marts/referencia/dim_cargos"


# ---------------------------------------------------------------- arquivos no lake (ADR 0037)

DOU = "staging/executivo/federal/dou/arq_secoes"
FOTOS = "staging/judiciario/federal/tse/arq_fotos"
JPG = b"\xff\xd8foto"
FOTO_LOCAL = "2022/RJ/1001.jpg"


def capture(
    con: Connection,
    settings: Settings,
    source: str,
    dataset: str,
    part: int,
    name: str,
    members: dict[str, bytes],
) -> None:
    """Uma captura no landing: um zip com os membros dados."""
    file = settings.landing_dir / source / dataset / str(part) / name
    file.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(file, "w") as package:
        for member, content in members.items():
            package.writestr(member, content)
    landing.register_capture(
        con,
        source,
        dataset,
        part,
        f"https://exemplo.gov.br/{dataset}/{part}.zip",
        hashlib.sha256(file.read_bytes()).hexdigest(),
        file.stat().st_size,
        file.relative_to(settings.storage_root).as_posix(),
        0,
    )


def land_files(con: Connection, settings: Settings, photo: bytes = JPG) -> None:
    """Capturas do DOU e de fotos do TSE (uma sem imagem) e uma não publicável; materializa todas."""
    capture(con, settings, "dou", "secao1", 202608, "base-0123456789ab.zip", {"a.xml": b"<a/>"})
    capture(con, settings, "tse", "fotos_rj", 2022, "fotos_rj-0123456789ab.zip", {"FRJ1001_div.jpg": photo})
    capture(con, settings, "tse", "fotos_ms", 2022, "fotos_ms-0123456789ab.zip", {"leiame.txt": b"sem foto"})
    capture(con, settings, "tse", "candidatos", 2022, "candidatos.zip", {"x.csv": b"x"})
    for source in ("dou", "tse"):
        arquivos.materialize(con, settings, contracts.find(source))


def control(out: Path, folder: str) -> list[dict[str, object]]:
    c = duckdb.connect()
    cur = c.execute(f"SELECT * FROM read_parquet('{where(out, folder).as_posix()}') ORDER BY caminho")
    names = [d[0] for d in cur.description]
    found = [dict(zip(names, r, strict=True)) for r in cur.fetchall()]
    c.close()
    return found


def test_files_are_materialized_once_from_the_contract_and_only_the_matching_members(
    con: Connection, settings: Settings
) -> None:
    land_files(con, settings)
    base = settings.storage_root / "arquivos"
    assert (base / "judiciario/federal/tse/arq_fotos" / FOTO_LOCAL).read_bytes() == JPG
    assert (base / "executivo/federal/dou/arq_secoes/secao1/202608/base.zip").exists()  # o hash sai do nome
    assert sorted(p.name for p in base.rglob("*") if p.is_file()) == ["1001.jpg", "base.zip"]
    assert arquivos.materialize(con, settings, contracts.find("tse")) == 0  # idempotente
    capture(
        con,
        settings,
        "tse",
        "fotos_rj",
        2022,
        "fotos_rj-ba9876543210.zip",
        {"FRJ1001_div.jpg": b"\xff\xd8nova!"},
    )
    assert (
        arquivos.materialize(con, settings, contracts.find("tse")) == 1
    )  # nova captura, mesmo caminho e tamanho diferente (mesmo tamanho não regrava)
    assert (base / "judiciario/federal/tse/arq_fotos" / FOTO_LOCAL).read_bytes() == b"\xff\xd8nova!"


def test_published_collections_are_copied_with_a_control_table_and_unpublished_ones_are_not(
    con: Connection, settings: Settings
) -> None:
    land_files(con, settings)
    out, _ = run(con, settings)
    dou, fotos = control(out, DOU), control(out, FOTOS)
    assert [(r["caminho"], r["fl_original"], r["content_type"]) for r in dou] == [
        ("secao1/202608/base.zip", True, mimetypes.guess_type("x.zip")[0])
    ]
    assert [(r["caminho"], r["fl_original"], r["content_type"]) for r in fotos] == [
        (FOTO_LOCAL, False, "image/jpeg")
    ]
    zip_bytes = (out / DOU / "secao1/202608/base.zip").read_bytes()
    assert dou[0]["sha256_arquivo"] == dou[0]["sha256_captura"] == hashlib.sha256(zip_bytes).hexdigest()
    assert (out / FOTOS / FOTO_LOCAL).read_bytes() == JPG
    assert fotos[0]["sha256_arquivo"] == hashlib.sha256(JPG).hexdigest()
    assert fotos[0]["sha256_captura"] != fotos[0]["sha256_arquivo"]  # a captura é o zip de origem
    assert fotos[0]["id_captura"] != dou[0]["id_captura"] and fotos[0]["fonte"] == "tse"
    assert fotos[0]["url_fonte"] == "https://exemplo.gov.br/fotos_rj/2022.zip" and fotos[0][
        "qtd_bytes"
    ] == len(JPG)
    assert not list((out / FOTOS).rglob("*.zip"))  # o zip das fotos não sobe
    tables = {t["tabela"]: t for t in manifest(out)["tabelas"]}
    assert tables["arq_secoes"]["caminho"] == DOU and tables["arq_fotos"]["caminho"] == FOTOS
    assert all(c["descricao"] for t in ("arq_secoes", "arq_fotos") for c in tables[t]["colunas"])  # type: ignore[attr-defined]
    assert kv(where(out, FOTOS))["descricao"]
    catalog = duckdb.connect(str(out / "catalogo.duckdb"), read_only=True)
    assert scalar(catalog, "SELECT comment FROM duckdb_views() WHERE view_name = 'arq_fotos'")
    catalog.close()


def test_only_missing_or_changed_files_are_sent_and_verify_checks_the_objects(
    monkeypatch: pytest.MonkeyPatch, con: Connection, settings: Settings
) -> None:
    land_files(con, settings)
    out, _ = run(con, settings)
    stamp = (out / FOTOS / FOTO_LOCAL).stat().st_mtime_ns
    sent: list[str] = []
    monkeypatch.setattr(shutil, "copyfile", lambda s, d: sent.append(Path(d).as_posix()))
    again = export.export(settings)
    assert again["gravadas"] == 0 and sent == []  # nenhum arquivo reenviado, nem o catálogo
    monkeypatch.undo()
    assert (out / FOTOS / FOTO_LOCAL).stat().st_mtime_ns == stamp
    assert verify.verify(settings) == []
    nova = b"\xff\xd8nova!"
    con = warehouse.connect(settings)
    capture(con, settings, "tse", "fotos_rj", 2022, "fotos_rj-ba9876543210.zip", {"FRJ1001_div.jpg": nova})
    arquivos.materialize(con, settings, contracts.find("tse"))
    con.close()
    export.export(settings)
    assert (out / FOTOS / FOTO_LOCAL).read_bytes() == nova and verify.verify(settings) == []
    (out / FOTOS / FOTO_LOCAL).write_bytes(b"adulterada")
    (out / FOTOS / "2022/RJ/solta.jpg").write_bytes(b"x")
    assert sorted(verify.verify(settings)) == [
        f"{FOTOS}/2022/RJ/1001.jpg difere do controle",
        f"{FOTOS}/2022/RJ/solta.jpg fora do controle",
    ]
    (out / DOU / "secao1/202608/base.zip").unlink()
    assert f"falta {DOU}/secao1/202608/base.zip" in verify.verify(settings)


def test_an_object_outside_the_control_stays_without_prune(con: Connection, settings: Settings) -> None:
    land_files(con, settings)
    out, _ = run(con, settings)
    (out / FOTOS / "2022/RJ/solta.jpg").write_bytes(b"x")
    con = warehouse.connect(settings)
    capture(
        con,
        settings,
        "tse",
        "fotos_rj",
        2022,
        "fotos_rj-ba9876543210.zip",
        {"FRJ1001_div.jpg": JPG, "FRJ1002_div.jpg": b"\xff\xd8outra"},
    )
    arquivos.materialize(con, settings, contracts.find("tse"))
    con.close()
    export.export(settings)
    assert len(control(out, FOTOS)) == 2 and (out / FOTOS / "2022/RJ/solta.jpg").exists()
    export.export(settings, prune=True)
    assert not (out / FOTOS / "2022/RJ/solta.jpg").exists()


def add_photos(settings: Settings, members: dict[str, bytes]) -> None:
    con = warehouse.connect(settings)
    capture(con, settings, "tse", "fotos_rj", 2022, "fotos_rj-ba9876543210.zip", members)
    arquivos.materialize(con, settings, contracts.find("tse"))
    con.close()


def test_a_crash_in_the_middle_of_the_send_resumes_without_resending(
    monkeypatch: pytest.MonkeyPatch, con: Connection, settings: Settings
) -> None:
    land_files(con, settings)
    out, _ = run(con, settings)
    add_photos(
        settings,
        {f"FRJ{n}_div.jpg": JPG + bytes([n % 256]) for n in range(1002, 1005)} | {"FRJ1001_div.jpg": JPG},
    )
    real, calls = shutil.copyfile, []

    def flaky(src: str, dst: str) -> object:
        if str(dst).endswith(".jpg"):
            calls.append(dst)
            if len(calls) == 3:
                raise OSError("queda")
        return real(src, dst)

    monkeypatch.setattr(shutil, "copyfile", flaky)
    with pytest.raises(OSError, match="queda"):
        export.export(settings)
    monkeypatch.undo()
    assert len(control(out, FOTOS)) == 1  # o controle publicado ainda é o antigo
    sent: list[str] = []

    def spy(src: str, dst: str) -> object:
        sent.append(str(dst))
        return real(src, dst)

    monkeypatch.setattr(shutil, "copyfile", spy)
    export.export(settings)
    monkeypatch.undo()
    assert len([d for d in sent if d.endswith(".jpg")]) == 1  # só o que faltava (2 de 3 já estavam)
    assert len(control(out, FOTOS)) == 4 and verify.verify(settings) == []


def test_a_crash_after_the_tables_keeps_them_and_resumes_without_rewriting(
    monkeypatch: pytest.MonkeyPatch, con: Connection, settings: Settings
) -> None:
    land_files(con, settings)
    out, _ = run(con, settings)
    change(settings, "INSERT INTO intermediate.int_x VALUES (2)")
    add_photos(settings, {"FRJ1001_div.jpg": JPG, "FRJ1002_div.jpg": JPG + b"2"})

    def crash(*args: object) -> None:
        raise OSError("queda")

    monkeypatch.setattr(colecoes, "send", crash)
    with pytest.raises(OSError, match="queda"):
        export.export(settings)
    monkeypatch.undo()
    assert next(t for t in manifest(out)["tabelas"] if t["tabela"] == "int_x")["linhas"] == 2
    int_x = where(out, "intermediate/int_x")
    stamp = int_x.stat().st_mtime_ns
    result = export.export(settings)
    assert where(out, "intermediate/int_x") == int_x and int_x.stat().st_mtime_ns == stamp
    assert result["gravadas"] == 1 and len(control(out, FOTOS)) == 2  # só a coleção
    assert verify.verify(settings) == []


def test_each_finished_collection_is_registered_before_the_next(
    monkeypatch: pytest.MonkeyPatch, con: Connection, settings: Settings
) -> None:
    land_files(con, settings)
    out, _ = run(con, settings)
    add_photos(settings, {"FRJ1001_div.jpg": JPG, "FRJ1002_div.jpg": JPG + b"2"})
    real, seen = colecoes.send, []

    def watch(root: str, key: str, files: list[dict[str, object]], known: dict[str, str]) -> tuple[int, int]:
        seen.append(len(control(out, FOTOS)))  # o que já estava registrado ao começar esta coleção
        return real(root, key, files, known)

    monkeypatch.setattr(colecoes, "send", watch)
    export.export(settings)
    assert len(control(out, FOTOS)) == 2 and set(seen) == {1}


def test_r2_list_follows_the_continuation_token_and_send_skips_existing_objects(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    pages = {
        "": b"<ListBucketResult xmlns='x'><Contents><Key>c/a.jpg</Key><Size>3</Size></Contents>"
        b"<IsTruncated>true</IsTruncated><NextContinuationToken>t1</NextContinuationToken></ListBucketResult>",
        "t1": b"<ListBucketResult xmlns='x'><Contents><Key>c/b.jpg</Key><Size>5</Size></Contents>"
        b"<IsTruncated>false</IsTruncated></ListBucketResult>",
    }
    puts: list[str] = []

    def fake(method: str, key: str, path: Path | None = None, *args: object, **kw: object) -> bytes:
        if method == "GET":
            query: dict[str, str] = kw["query"]  # type: ignore[assignment]
            assert query["prefix"] == "c/" and query["list-type"] == "2"
            return pages[query.get("continuation-token", "")]
        puts.append(key)
        return b""

    monkeypatch.setattr(lake, "request", fake)
    monkeypatch.setattr(s3, "request", lambda cfg, *a, **kw: fake(*a, **kw))
    assert s3.list_objects({}, "c/") == {"c/a.jpg": 3, "c/b.jpg": 5}
    files = [
        {"caminho": n, "sha256_arquivo": "h", "qtd_bytes": q, "content_type": "image/jpeg", "local": tmp_path}
        for n, q in (("a.jpg", 3), ("b.jpg", 9), ("c.jpg", 1))
    ]
    # a.jpg já existe com o mesmo tamanho; b.jpg existe com tamanho diferente; c.jpg falta
    assert colecoes.send("r2://b", "c", files, {}) == (2, 1) and sorted(puts) == ["c/b.jpg", "c/c.jpg"]


def test_the_file_phase_runs_on_a_fresh_connection_and_inserts_are_not_order_preserving(
    monkeypatch: pytest.MonkeyPatch, con: Connection, settings: Settings
) -> None:
    land_files(con, settings)
    run(con, settings)
    add_photos(settings, {"FRJ1001_div.jpg": JPG, "FRJ1002_div.jpg": JPG + b"2"})
    seen: list[tuple[int, bool]] = []
    real = colecoes.control

    def spy(c: Connection, *args: object) -> object:
        tables = scalar(c, "SELECT count(*) FROM duckdb_tables() WHERE schema_name = 'marts'")
        seen.append((tables, scalar(c, "SELECT current_setting('preserve_insertion_order')")))
        return real(c, *args)  # type: ignore[arg-type]

    monkeypatch.setattr(colecoes, "control", spy)
    export.export(settings)
    assert seen == [(0, False)]  # sem o warehouse (memória das tabelas liberada) e sem ordem preservada


def test_a_file_missing_on_disk_stops_the_export_unless_pruned(con: Connection, settings: Settings) -> None:
    land_files(con, settings)
    out, _ = run(con, settings)
    (settings.storage_root / "arquivos/judiciario/federal/tse/arq_fotos" / FOTO_LOCAL).unlink()
    with pytest.raises(ValueError, match="--prune"):
        export.export(settings)
    assert (out / FOTOS / FOTO_LOCAL).exists() and len(control(out, FOTOS)) == 1  # nada encolheu
    export.export(settings, prune=True)
    assert not (out / FOTOS / FOTO_LOCAL).exists() and control(out, FOTOS) == []


def test_a_published_collection_that_left_the_contract_stops_the_export_unless_pruned(
    monkeypatch: pytest.MonkeyPatch, con: Connection, settings: Settings
) -> None:
    land_files(con, settings)
    out, _ = run(con, settings)
    monkeypatch.setattr(colecoes, "_published", lambda dataset: False)
    with pytest.raises(ValueError, match="--prune"):
        export.export(settings)
    assert (out / FOTOS / FOTO_LOCAL).exists() and (out / DOU / "secao1/202608/base.zip").exists()
    export.export(settings, prune=True)
    assert not (out / FOTOS / FOTO_LOCAL).exists()
    assert {t["tabela"] for t in manifest(out)["tabelas"]}.isdisjoint({"arq_fotos", "arq_secoes"})


def test_publicar_only_counts_when_it_is_exactly_true() -> None:
    assert colecoes._published({"files": {"publish": True}})
    assert not any(colecoes._published({"files": {"publish": v}}) for v in ("false", "sim", 1, None))
    assert not colecoes._published({}) and not colecoes._published({"arquivos": None})


@pytest.mark.parametrize("var", ["DADO_PUBLICO_R2_BUCKET", "DADO_PUBLICO_LAKE_URL"])
def test_a_partial_r2_configuration_fails_instead_of_exporting_locally(
    var: str, con: Connection, settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    for name in ("ACCOUNT_ID", "ACCESS_KEY_ID", "SECRET_ACCESS_KEY", "BUCKET"):
        monkeypatch.delenv(f"DADO_PUBLICO_R2_{name}", raising=False)
    monkeypatch.delenv("DADO_PUBLICO_LAKE_URL", raising=False)
    monkeypatch.setenv(var, "x")
    with pytest.raises(ValueError, match="R2 incompleto"):
        export.export(settings)


def dbt_nodes(settings: Settings, nodes: dict[str, dict[str, object]]) -> None:
    """Manifesto do dbt sintético com os nós dados, além do mart de votos."""
    target = settings.state_dir / "dbt" / "target"
    full = {**MODELS["nodes"], **nodes}
    (target / "manifest.json").write_text(json.dumps({"nodes": full}), encoding="utf-8")


def record_results(settings: Settings, stage: str, results: dict[str, str]) -> None:
    live = warehouse.connect(settings)
    row = live.execute(
        "INSERT INTO metadata.execucoes (etapa, fonte, dt_inicio, resultado) VALUES (?, 'dbt', now() AT TIME ZONE 'UTC', 'ok') "
        "RETURNING id_execucao",
        (stage,),
    ).fetchone()
    assert row is not None
    run_id = row[0]
    live.executemany(
        "INSERT INTO metadata.testes_resultados (id_execucao, id_no, tipo, resultado, dt_registro) "
        "VALUES (?, ?, ?, ?, now())",
        [(run_id, k, "test" if k.startswith("test.") else "model", v) for k, v in results.items()],
    )
    live.close()


def test_a_failing_model_or_test_keeps_its_previous_version_and_the_rest_is_published(
    con: Connection, settings: Settings
) -> None:
    out, first = run(con, settings)
    dbt_nodes(
        settings,
        {
            "model.x.int_x": {"resource_type": "model", "name": "int_x", "schema": "intermediate"},
            "model.x.fct_votos": {**MODELS["nodes"]["model.x.fct_votos"], "schema": "marts"},
            "model.x.stg_camara__base": {
                "resource_type": "model",
                "name": "stg_camara__base",
                "schema": "staging",
            },
            "test.x.not_null_votos": {
                "resource_type": "test",
                "name": "not_null_votos",
                "attached_node": "model.x.fct_votos",
                "depends_on": {"nodes": ["model.x.fct_votos"]},
            },
            "test.x.singular_dos_dois": {
                "resource_type": "test",
                "name": "singular_dos_dois",
                "depends_on": {"nodes": ["model.x.int_x", "model.x.stg_camara__base"]},
            },
        },
    )
    change(settings, "UPDATE marts.fct_votos SET qtd = qtd + 1")  # esta versão não pode sair (teste em erro)
    change(settings, "UPDATE staging.stg_camara__base SET nome = 'novo'")  # esta sai
    change(settings, "UPDATE intermediate.int_x SET a = 2")  # modelo em erro: fica a anterior
    record_results(
        settings,
        "transform_post",
        {
            "test.x.not_null_votos": "fail",
            "model.x.int_x": "error",
            "model.x.stg_camara__base": "success",
            "test.x.singular_dos_dois": "pass",
        },
    )
    before = {t["tabela"]: t for t in manifest(out)["tabelas"]}
    result = export.export(settings)
    after = {t["tabela"]: t for t in manifest(out)["tabelas"]}
    assert (
        result["excluidas"] == 2 and result["gravadas"] == 3
    )  # a base, a view sobre ela e o histórico dos testes
    assert after["fct_votos"]["impressao"] == before["fct_votos"]["impressao"]  # a anterior, intacta
    assert "teste not_null_votos: fail" in str(after["fct_votos"]["excluida_por"])
    assert "modelo int_x: error" in str(after["int_x"]["excluida_por"])
    assert "excluida_por" not in after["stg_camara__base"]
    assert after["stg_camara__base"]["impressao"] != before["stg_camara__base"]["impressao"]
    assert verify.verify(settings) == []  # o publicado continua íntegro, inclusive as versões mantidas
    catalog = duckdb.connect(str(out / "catalogo.duckdb"), read_only=True)
    comment = catalog.execute("SELECT comment FROM duckdb_views() WHERE view_name = 'fct_votos'").fetchone()
    assert comment is not None and "versão anterior" in comment[0]
    catalog.close()
    record_results(  # corrigido na execução seguinte: volta a ser publicado, sem o motivo
        settings,
        "transform_post",
        {"test.x.not_null_votos": "pass", "model.x.int_x": "success"},
    )
    export.export(settings)
    fixed = {t["tabela"]: t for t in manifest(out)["tabelas"]}
    assert "excluida_por" not in fixed["fct_votos"] and "excluida_por" not in fixed["int_x"]
    assert fixed["fct_votos"]["impressao"] != before["fct_votos"]["impressao"]


def test_a_table_that_never_reached_the_lake_and_failed_is_not_published(
    con: Connection, settings: Settings
) -> None:
    build(con, settings)
    con.close()
    dbt_nodes(
        settings, {"model.x.int_x": {"resource_type": "model", "name": "int_x", "schema": "intermediate"}}
    )
    record_results(settings, "transform_pre", {"model.x.int_x": "skipped"})
    result = export.export(settings)
    names = {
        t["tabela"]
        for t in json.loads((settings.storage_root / "lake/manifesto.json").read_text())["tabelas"]
    }
    assert result["excluidas"] == 1 and "int_x" not in names and "fct_votos" in names


def build_at(settings: Settings, when: str, results: dict[str, str]) -> None:
    """Uma execução do dbt que começou em `when` (ISO), com o resultado de cada nó."""
    live = warehouse.connect(settings)
    row = live.execute(
        "INSERT INTO metadata.execucoes (etapa, fonte, dt_inicio, resultado) "
        "VALUES ('transform_post', 'dbt', ?, 'ok') RETURNING id_execucao",
        (when,),
    ).fetchone()
    assert row is not None
    live.executemany(
        "INSERT INTO metadata.testes_resultados (id_execucao, id_no, tipo, resultado, dt_registro) "
        "VALUES (?, ?, 'model', ?, now())",
        [(row[0], k, v) for k, v in results.items()],
    )
    live.close()


def test_a_table_not_rebuilt_since_the_published_manifest_is_not_fingerprinted_again(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture, con: Connection, settings: Settings
) -> None:
    """ADR 0047: o manifesto sai idêntico ao do export completo, sem ler a tabela que o dbt não refez."""
    monkeypatch.setattr(runs, "code_version", lambda: "abc123")  # a árvore de trabalho suja nunca reaproveita
    out, _ = run(con, settings)
    dbt_nodes(
        settings,
        {
            "model.x.int_x": {"resource_type": "model", "name": "int_x", "schema": "intermediate"},
            "model.x.fct_votos": {**MODELS["nodes"]["model.x.fct_votos"], "schema": "marts"},
        },
    )
    complete = manifest(out)["tabelas"]
    build_at(
        settings, "2020-01-01T00:00:00+00:00", {"model.x.int_x": "success", "model.x.fct_votos": "success"}
    )
    seen: list[str] = []
    original = tables.fingerprint

    def spy(con_: object, schema: str, table: str, *rest: object) -> object:
        seen.append(f"{schema}.{table}")
        return original(con_, schema, table, *rest)  # type: ignore[arg-type]

    monkeypatch.setattr(tables, "fingerprint", spy)
    caplog.clear()
    caplog.set_level(logging.INFO)
    result = export.export(settings)
    assert sorted(seen) == [  # só as sem nó do dbt no manifesto (staging e metadata): sempre recalculadas
        "metadata.capturas",
        "metadata.fontes_verificacoes",
        "metadata.testes_resultados",
        "staging.stg_camara__base",
        "staging.stg_camara__visao",
        "staging.stg_tse__x",
    ]
    # o histórico dos testes ganhou as linhas do `build_at`: é a única tabela que muda
    rest = [t for t in manifest(out)["tabelas"] if t["tabela"] != "testes_resultados"]
    assert rest == [t for t in complete if t["tabela"] != "testes_resultados"] and result["gravadas"] == 1
    assert "int_x: reaproveitada" in caplog.text
    assert verify.verify(settings) == []

    # refeita depois do manifesto: a impressão é recalculada e o dado novo é publicado
    change(settings, "INSERT INTO intermediate.int_x VALUES (2)")
    build_at(settings, "2999-01-01T00:00:00+00:00", {"model.x.int_x": "success"})
    seen.clear()
    result = export.export(settings)
    assert (
        "intermediate.int_x" in seen and "marts.fct_votos" not in seen and result["gravadas"] == 2
    )  # int_x e o histórico


def test_a_new_code_version_fingerprints_everything_again(
    monkeypatch: pytest.MonkeyPatch, con: Connection, settings: Settings
) -> None:
    monkeypatch.setattr(runs, "code_version", lambda: "abc123")
    run(con, settings)
    dbt_nodes(settings, {"model.x.fct_votos": {**MODELS["nodes"]["model.x.fct_votos"], "schema": "marts"}})
    build_at(settings, "2020-01-01T00:00:00+00:00", {"model.x.fct_votos": "success"})
    calls: list[str] = []
    original = tables.fingerprint

    def spy(c: object, s: str, t: str, *a: object) -> object:
        calls.append(t)
        return original(c, s, t, *a)  # type: ignore[arg-type]

    monkeypatch.setattr(tables, "fingerprint", spy)
    export.export(settings)
    assert "fct_votos" not in calls
    calls.clear()
    monkeypatch.setattr(runs, "code_version", lambda: "outro-commit")  # descrições e chaves vêm do código
    export.export(settings)
    assert "fct_votos" in calls


GOLDEN: dict[int, list[tuple[object, ...]]] = {
    128 << 20: [
        (
            "staging",
            "stg_camara__base",
            "staging/legislativo/federal/camara/stg_camara__base",
            50,
            "ad18b58c63ed43d342cb788fd456e4d268b505628e4b108cd5c8bb0fdd1003e0",
            None,
            None,
            None,
            [("id", "BIGINT", ""), ("nome", "VARCHAR", "")],
            [("staging/legislativo/federal/camara/stg_camara__base.parquet", 50)],
        ),
        (
            "staging",
            "stg_camara__visao",
            "staging/legislativo/federal/camara/stg_camara__visao",
            50,
            "eeed9b56b7a43686f8a35c32b53bc67cc4842deb9e54d9cc462172ae45765d7b",
            None,
            None,
            None,
            [("id", "BIGINT", ""), ("nome", "VARCHAR", "")],
            [("staging/legislativo/federal/camara/stg_camara__visao.parquet", 50)],
        ),
        (
            "staging",
            "stg_tse__x",
            "staging/judiciario/federal/tse/stg_tse__x",
            1,
            "35937610f19a5f8cbf019ce1fce676e5053ea61b472ea80c119134dd45581477",
            None,
            None,
            "CC BY",
            [("a", "INTEGER", "")],
            [("staging/judiciario/federal/tse/stg_tse__x.parquet", 1)],
        ),
        (
            "intermediate",
            "int_x",
            "intermediate/int_x",
            1,
            "f288f0dd6d06840a67bfa99875859e35384eb783243cf6c8e0a5d1836bda34ce",
            None,
            None,
            None,
            [("a", "INTEGER", "")],
            [("intermediate/int_x.parquet", 1)],
        ),
        (
            "marts",
            "fct_votos",
            "marts/legislativo/fct_votos",
            1000,
            "1c5642eccbe36ce18031bfb1a04ad771e52955ef0992f4eb2909db4345ed47a6",
            "year(dt_voto)",
            None,
            None,
            [
                ("id_voto", "BIGINT", ""),
                ("dt_voto", "TIMESTAMP", ""),
                ("qtd", "BIGINT", "Quantidade de teste."),
            ],
            [("marts/legislativo/fct_votos.parquet", 1000)],
        ),
        (
            "metadata",
            "capturas",
            "metadata/capturas",
            0,
            "dd00fef441775491d01eeb3c598484248953ed85fd81245bcfb9ff2b917d040a",
            None,
            None,
            None,
            [
                (
                    "id_captura",
                    "BIGINT",
                    "Identificador da captura; as tabelas do raw o guardam como _source_file_id.",
                ),
                ("fonte", "VARCHAR", "Fonte do arquivo."),
                ("dataset", "VARCHAR", "Dataset do arquivo."),
                (
                    "particao",
                    "INTEGER",
                    "Partição do arquivo (ano, mês AAAAMM ou legislatura); vazio nos datasets sem partição.",
                ),
                ("url", "VARCHAR", "Endereço oficial de onde o arquivo foi baixado."),
                (
                    "sha256",
                    "VARCHAR",
                    "Impressão digital (SHA-256) do arquivo: prova que o arquivo guardado é o que a fonte entregou.",
                ),
                ("qtd_bytes", "BIGINT", "Tamanho do arquivo em bytes."),
                ("caminho", "VARCHAR", "Caminho do arquivo no landing, a partir da pasta de armazenamento."),
                ("dt_captura", "TIMESTAMP", "Instante (UTC) da primeira captura deste conteúdo."),
                (
                    "dt_verificacao",
                    "TIMESTAMP",
                    "Instante (UTC) da última vez que a fonte foi consultada e o conteúdo continuava o mesmo.",
                ),
                ("id_execucao", "BIGINT", "Execução (metadata.execucoes.id_execucao) que fez a captura."),
                ("etag", "VARCHAR", "ETag que a fonte informou na captura, quando informou."),
                (
                    "ultima_modificacao",
                    "VARCHAR",
                    "Cabeçalho Last-Modified que a fonte informou na captura, como publicado, quando informou.",
                ),
                (
                    "dt_carga",
                    "TIMESTAMP",
                    "Instante (UTC) em que o arquivo foi carregado no raw; vazio se ainda não foi.",
                ),
            ],
            [("metadata/capturas.parquet", 0)],
        ),
        (
            "metadata",
            "fontes_verificacoes",
            "metadata/fontes_verificacoes",
            0,
            "662a89f035601869bdbd8480a69e94d3700a2efd21625a219e040453cc974c4a",
            None,
            None,
            None,
            [
                ("id_verificacao", "BIGINT", "Identificador da verificação."),
                ("dt_verificacao", "TIMESTAMP", "Instante (UTC) da verificação."),
                ("fonte", "VARCHAR", "Fonte verificada."),
                ("dataset", "VARCHAR", "Dataset verificado."),
                (
                    "particao",
                    "INTEGER",
                    "Partição verificada (ano, mês AAAAMM ou legislatura), quando houver.",
                ),
                (
                    "verificacao",
                    "VARCHAR",
                    "Nome da verificação (availability, schema, volume, carga, linhas_removidas...).",
                ),
                ("resultado", "VARCHAR", "Resultado: ok, warn (aviso) ou error (erro)."),
                (
                    "detalhe",
                    "VARCHAR",
                    "Detalhe do resultado (contagens, colunas que mudaram, mensagem de erro).",
                ),
                (
                    "cd_status_http",
                    "INTEGER",
                    "Código HTTP que a fonte devolveu (404, 403, 429...), quando a ocorrência veio de uma resposta; vazio nas demais.",
                ),
                (
                    "tipo_ocorrencia",
                    "VARCHAR",
                    "Tipo da ocorrência de uma verificação com erro: nao_encontrado (404), nao_publicado (403 no mês ainda não publicado), erro_http (outro código), falha_de_rede, bloqueio, html_no_lugar, tamanho_divergente ou zip_invalido; vazio quando não há ocorrência.",
                ),
                (
                    "qtd_bytes_esperados",
                    "BIGINT",
                    "Tamanho em bytes que a fonte informou (Content-Length), quando a verificação o confrontou com o recebido.",
                ),
                (
                    "qtd_bytes_recebidos",
                    "BIGINT",
                    "Tamanho em bytes do arquivo recebido, nas verificações de disponibilidade e de integridade.",
                ),
                (
                    "qtd_linhas",
                    "BIGINT",
                    "Linhas da verificação: carregadas (carga), lidas (volume) ou de capturas anteriores que a atual não traz (linhas_removidas).",
                ),
            ],
            [("metadata/fontes_verificacoes.parquet", 0)],
        ),
        (
            "metadata",
            "testes_resultados",
            "metadata/testes_resultados",
            0,
            "fef1f18e8143048b4963b92868dd83e861fcc60c137df0bb915ecf1cf98301f7",
            None,
            None,
            None,
            [
                ("id_execucao", "BIGINT", "Execução (metadata.execucoes.id_execucao) que rodou o dbt."),
                (
                    "id_no",
                    "VARCHAR",
                    "Identificador do nó no dbt (por exemplo, test.dado_publico_brasil.nome_do_teste).",
                ),
                ("tipo", "VARCHAR", "Tipo do nó: model, test ou freshness."),
                ("resultado", "VARCHAR", "Resultado: success, pass, warn, fail ou error."),
                ("qtd_falhas", "BIGINT", "Linhas que fizeram o teste falhar ou avisar."),
                ("mensagem", "VARCHAR", "Mensagem do dbt para o nó."),
                ("dt_registro", "TIMESTAMP", "Instante (UTC) em que o resultado foi gravado."),
                (
                    "qtd_segundos",
                    "DOUBLE",
                    "Segundos que o dbt levou para executar o nó (execution_time do run_results.json); vazio se o "
                    "dbt não informou.",
                ),
            ],
            [("metadata/testes_resultados.parquet", 0)],
        ),
    ],
    1: [
        (
            "staging",
            "stg_camara__base",
            "staging/legislativo/federal/camara/stg_camara__base",
            50,
            "ad18b58c63ed43d342cb788fd456e4d268b505628e4b108cd5c8bb0fdd1003e0",
            None,
            None,
            None,
            [("id", "BIGINT", ""), ("nome", "VARCHAR", "")],
            [("staging/legislativo/federal/camara/stg_camara__base.parquet", 50)],
        ),
        (
            "staging",
            "stg_camara__visao",
            "staging/legislativo/federal/camara/stg_camara__visao",
            50,
            "eeed9b56b7a43686f8a35c32b53bc67cc4842deb9e54d9cc462172ae45765d7b",
            None,
            None,
            None,
            [("id", "BIGINT", ""), ("nome", "VARCHAR", "")],
            [("staging/legislativo/federal/camara/stg_camara__visao.parquet", 50)],
        ),
        (
            "staging",
            "stg_tse__x",
            "staging/judiciario/federal/tse/stg_tse__x",
            1,
            "35937610f19a5f8cbf019ce1fce676e5053ea61b472ea80c119134dd45581477",
            None,
            None,
            "CC BY",
            [("a", "INTEGER", "")],
            [("staging/judiciario/federal/tse/stg_tse__x.parquet", 1)],
        ),
        (
            "intermediate",
            "int_x",
            "intermediate/int_x",
            1,
            "f288f0dd6d06840a67bfa99875859e35384eb783243cf6c8e0a5d1836bda34ce",
            None,
            None,
            None,
            [("a", "INTEGER", "")],
            [("intermediate/int_x.parquet", 1)],
        ),
        (
            "marts",
            "fct_votos",
            "marts/legislativo/fct_votos",
            1000,
            "1c5642eccbe36ce18031bfb1a04ad771e52955ef0992f4eb2909db4345ed47a6",
            "year(dt_voto)",
            [2020, 2021, 2022],
            None,
            [
                ("id_voto", "BIGINT", ""),
                ("dt_voto", "TIMESTAMP", ""),
                ("qtd", "BIGINT", "Quantidade de teste."),
                ("ano", "BIGINT", "Ano da partição: year(dt_voto)."),
            ],
            [
                ("marts/legislativo/fct_votos/ano=2020/part-0.parquet", 334),
                ("marts/legislativo/fct_votos/ano=2021/part-0.parquet", 333),
                ("marts/legislativo/fct_votos/ano=2022/part-0.parquet", 333),
            ],
        ),
        (
            "metadata",
            "capturas",
            "metadata/capturas",
            0,
            "dd00fef441775491d01eeb3c598484248953ed85fd81245bcfb9ff2b917d040a",
            None,
            None,
            None,
            [
                (
                    "id_captura",
                    "BIGINT",
                    "Identificador da captura; as tabelas do raw o guardam como _source_file_id.",
                ),
                ("fonte", "VARCHAR", "Fonte do arquivo."),
                ("dataset", "VARCHAR", "Dataset do arquivo."),
                (
                    "particao",
                    "INTEGER",
                    "Partição do arquivo (ano, mês AAAAMM ou legislatura); vazio nos datasets sem partição.",
                ),
                ("url", "VARCHAR", "Endereço oficial de onde o arquivo foi baixado."),
                (
                    "sha256",
                    "VARCHAR",
                    "Impressão digital (SHA-256) do arquivo: prova que o arquivo guardado é o que a fonte entregou.",
                ),
                ("qtd_bytes", "BIGINT", "Tamanho do arquivo em bytes."),
                ("caminho", "VARCHAR", "Caminho do arquivo no landing, a partir da pasta de armazenamento."),
                ("dt_captura", "TIMESTAMP", "Instante (UTC) da primeira captura deste conteúdo."),
                (
                    "dt_verificacao",
                    "TIMESTAMP",
                    "Instante (UTC) da última vez que a fonte foi consultada e o conteúdo continuava o mesmo.",
                ),
                ("id_execucao", "BIGINT", "Execução (metadata.execucoes.id_execucao) que fez a captura."),
                ("etag", "VARCHAR", "ETag que a fonte informou na captura, quando informou."),
                (
                    "ultima_modificacao",
                    "VARCHAR",
                    "Cabeçalho Last-Modified que a fonte informou na captura, como publicado, quando informou.",
                ),
                (
                    "dt_carga",
                    "TIMESTAMP",
                    "Instante (UTC) em que o arquivo foi carregado no raw; vazio se ainda não foi.",
                ),
            ],
            [("metadata/capturas.parquet", 0)],
        ),
        (
            "metadata",
            "fontes_verificacoes",
            "metadata/fontes_verificacoes",
            0,
            "662a89f035601869bdbd8480a69e94d3700a2efd21625a219e040453cc974c4a",
            None,
            None,
            None,
            [
                ("id_verificacao", "BIGINT", "Identificador da verificação."),
                ("dt_verificacao", "TIMESTAMP", "Instante (UTC) da verificação."),
                ("fonte", "VARCHAR", "Fonte verificada."),
                ("dataset", "VARCHAR", "Dataset verificado."),
                (
                    "particao",
                    "INTEGER",
                    "Partição verificada (ano, mês AAAAMM ou legislatura), quando houver.",
                ),
                (
                    "verificacao",
                    "VARCHAR",
                    "Nome da verificação (availability, schema, volume, carga, linhas_removidas...).",
                ),
                ("resultado", "VARCHAR", "Resultado: ok, warn (aviso) ou error (erro)."),
                (
                    "detalhe",
                    "VARCHAR",
                    "Detalhe do resultado (contagens, colunas que mudaram, mensagem de erro).",
                ),
                (
                    "cd_status_http",
                    "INTEGER",
                    "Código HTTP que a fonte devolveu (404, 403, 429...), quando a ocorrência veio de uma resposta; vazio nas demais.",
                ),
                (
                    "tipo_ocorrencia",
                    "VARCHAR",
                    "Tipo da ocorrência de uma verificação com erro: nao_encontrado (404), nao_publicado (403 no mês ainda não publicado), erro_http (outro código), falha_de_rede, bloqueio, html_no_lugar, tamanho_divergente ou zip_invalido; vazio quando não há ocorrência.",
                ),
                (
                    "qtd_bytes_esperados",
                    "BIGINT",
                    "Tamanho em bytes que a fonte informou (Content-Length), quando a verificação o confrontou com o recebido.",
                ),
                (
                    "qtd_bytes_recebidos",
                    "BIGINT",
                    "Tamanho em bytes do arquivo recebido, nas verificações de disponibilidade e de integridade.",
                ),
                (
                    "qtd_linhas",
                    "BIGINT",
                    "Linhas da verificação: carregadas (carga), lidas (volume) ou de capturas anteriores que a atual não traz (linhas_removidas).",
                ),
            ],
            [("metadata/fontes_verificacoes.parquet", 0)],
        ),
        (
            "metadata",
            "testes_resultados",
            "metadata/testes_resultados",
            0,
            "fef1f18e8143048b4963b92868dd83e861fcc60c137df0bb915ecf1cf98301f7",
            None,
            None,
            None,
            [
                ("id_execucao", "BIGINT", "Execução (metadata.execucoes.id_execucao) que rodou o dbt."),
                (
                    "id_no",
                    "VARCHAR",
                    "Identificador do nó no dbt (por exemplo, test.dado_publico_brasil.nome_do_teste).",
                ),
                ("tipo", "VARCHAR", "Tipo do nó: model, test ou freshness."),
                ("resultado", "VARCHAR", "Resultado: success, pass, warn, fail ou error."),
                ("qtd_falhas", "BIGINT", "Linhas que fizeram o teste falhar ou avisar."),
                ("mensagem", "VARCHAR", "Mensagem do dbt para o nó."),
                ("dt_registro", "TIMESTAMP", "Instante (UTC) em que o resultado foi gravado."),
                (
                    "qtd_segundos",
                    "DOUBLE",
                    "Segundos que o dbt levou para executar o nó (execution_time do run_results.json); vazio se o "
                    "dbt não informou.",
                ),
            ],
            [("metadata/testes_resultados.parquet", 0)],
        ),
    ],
}


def shape(out: Path) -> list[tuple[object, ...]]:
    """O manifesto sem o que muda a cada execução (instante, bytes e SHA-256 do Parquet levam o instante)."""
    return [
        (
            t["camada"],
            t["tabela"],
            t["caminho"],
            t["linhas"],
            t["impressao"],
            t["particao"],
            t["ano"],
            t["licenca"],
            [(c["nome"], c["tipo"], c["descricao"]) for c in t["colunas"]],  # type: ignore[attr-defined]
            [(plain(f["arquivo"]), f["linhas"]) for f in t["arquivos"]],  # type: ignore[attr-defined]
        )
        for t in manifest(out)["tabelas"]
    ]


@pytest.mark.parametrize("max_bytes", [tables.MAX_BYTES, 1])
def test_the_manifest_of_the_synthetic_warehouse_is_the_one_recorded_before_splitting_the_module(
    max_bytes: int, con: Connection, settings: Settings
) -> None:
    out, _ = run(con, settings, max_bytes)
    assert shape(out) == GOLDEN[max_bytes]


def freeze_clock(monkeypatch: pytest.MonkeyPatch) -> None:
    """Todas as execuções caem no mesmo segundo (o id tem resolução de segundo)."""

    class Fixed(datetime):
        @classmethod
        def now(cls, tz: object = None) -> "Fixed":
            return cls(2030, 1, 1, 12, 0, 0, tzinfo=UTC)

    monkeypatch.setattr(export, "datetime", Fixed)


def test_two_exports_in_the_same_second_never_share_a_path(
    monkeypatch: pytest.MonkeyPatch, con: Connection, settings: Settings
) -> None:
    freeze_clock(monkeypatch)
    out, _ = run(con, settings)
    old_file = where(out, "intermediate/int_x")
    change(settings, "INSERT INTO intermediate.int_x VALUES (2)")
    export.export(settings)
    assert where(out, "intermediate/int_x") != old_file  # id repetido ganha sufixo
    assert verify.verify(settings) == []


def test_a_failure_in_the_middle_of_the_export_keeps_the_published_catalog_and_manifest(
    monkeypatch: pytest.MonkeyPatch, con: Connection, settings: Settings
) -> None:
    freeze_clock(monkeypatch)  # a execução que cai tem o mesmo id da publicada
    out, _ = run(con, settings)
    published = {n: (out / n).read_bytes() for n in ("catalogo.duckdb", "manifesto.json")}
    change(settings, "INSERT INTO intermediate.int_x VALUES (2)")
    change(settings, "INSERT INTO marts.fct_votos VALUES (5000, DATE '2021-01-01', 'x', 1)")
    real, calls = tables.write_table, []

    def crash(*args: object, **kwargs: object) -> list[dict[str, object]]:
        calls.append(1)
        if len(calls) == 2:
            raise OSError("queda")
        return real(*args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(tables, "write_table", crash)
    with pytest.raises(OSError, match="queda"):
        export.export(settings)
    assert len(calls) == 2  # a primeira tabela chegou a ser gravada, em caminho próprio
    assert {n: (out / n).read_bytes() for n in published} == published
    assert verify.verify(settings) == []  # o publicado segue íntegro: nada foi sobrescrito


def test_the_manifest_of_the_tables_is_the_same_in_rows_and_hash_after_an_incremental_run(
    con: Connection, settings: Settings
) -> None:
    out, _ = run(con, settings)
    first = {t["caminho"]: t for t in manifest(out)["tabelas"]}
    change(settings, "INSERT INTO intermediate.int_x VALUES (2)")
    export.export(settings)
    second = {t["caminho"]: t for t in manifest(out)["tabelas"]}
    assert second.keys() == first.keys()
    assert {k for k in first if first[k] != second[k]} == {"intermediate/int_x"}  # só a que mudou
    live = warehouse.connect(settings, read_only=True)
    for t in second.values():
        files = ", ".join(f"'{(out / f['arquivo']).as_posix()}'" for f in t["arquivos"])  # type: ignore[attr-defined]
        cols = ", ".join(f'"{c["nome"]}"' for c in t["colunas"])  # type: ignore[attr-defined]
        count = "SELECT count(*), sum(hash(t)::HUGEINT) FROM"
        want = live.execute(f'{count} (SELECT {cols} FROM {t["camada"]}."{t["tabela"]}") t').fetchone()
        assert live.execute(f"{count} read_parquet([{files}]) t").fetchone() == want, t["caminho"]
    live.close()


def test_the_first_export_of_the_month_fixes_an_immutable_dated_version_with_the_datapackage(
    monkeypatch: pytest.MonkeyPatch, con: Connection, settings: Settings
) -> None:
    monkeypatch.setattr(lake, "snapshot", SNAPSHOT)
    out, _ = run(con, settings)
    (folder,) = (out / "versoes").iterdir()
    assert re.fullmatch(r"\d{4}-\d{2}", folder.name)
    frozen = {n: (folder / n).read_bytes() for n in ("manifesto.json", "catalogo.duckdb", "datapackage.json")}
    version = json.loads(frozen["manifesto.json"])
    assert version.pop("versao") == folder.name and version == json.loads(
        (out / "manifesto.json").read_text()
    )
    old_file = where(out, VOTOS)
    change(settings, "INSERT INTO marts.fct_votos VALUES (5000, DATE '2021-01-01', 'x', 1)")
    export.export(settings)
    assert {n: (folder / n).read_bytes() for n in frozen} == frozen  # a versão do mês não se reescreve
    assert where(out, VOTOS) != old_file and old_file.exists()  # e os Parquet que ela cita ficam
    for t in json.loads(frozen["manifesto.json"])["tabelas"]:
        for f in t["arquivos"]:
            assert hashlib.sha256((out / f["arquivo"]).read_bytes()).hexdigest() == f["sha256"]
    pkg = json.loads(frozen["datapackage.json"])
    assert pkg["version"] == folder.name and len(pkg["resources"]) == len(version["tabelas"])
    res = next(r for r in pkg["resources"] if r["name"] == "marts.fct_votos")
    assert (
        res["hash"]
        == f"sha256:{next(t for t in version['tabelas'] if t['tabela'] == 'fct_votos')['arquivos'][0]['sha256']}"
        and res["format"] == "parquet"
    )
    assert {f["name"]: f["type"] for f in res["schema"]["fields"]} == {
        "id_voto": "integer",
        "dt_voto": "datetime",
        "qtd": "integer",
    }
    cat = duckdb.connect(str(folder / "catalogo.duckdb"), read_only=True)
    assert scalar(cat, "SELECT count(*) FROM marts.fct_votos") == 1000  # o número citado se reproduz
    cat.close()
    assert (
        json.loads((out / "datapackage.json").read_text())["version"]
        == json.loads((out / "manifesto.json").read_text())["id_execucao"]
    )


def _old_version(
    monkeypatch: pytest.MonkeyPatch, con: Connection, settings: Settings, month: str
) -> tuple[Path, Path, Path]:
    """Versão `month` que cita um Parquet que o lake atual já não usa: (lake, versão, arquivo só dela)."""
    monkeypatch.setattr(lake, "snapshot", SNAPSHOT)
    monkeypatch.setattr(lake, "utcnow", lambda: datetime.fromisoformat(f"{month}-05T00:00:00+00:00"))
    out, _ = run(con, settings)
    old_file = where(out, VOTOS)
    change(settings, "INSERT INTO marts.fct_votos VALUES (5000, DATE '2021-01-01', 'x', 1)")
    export.export(settings)
    assert old_file.exists() and where(out, VOTOS) != old_file
    return out, out / "versoes" / month, old_file


def _cited(out: Path) -> list[Path]:
    return [out / f["arquivo"] for t in manifest(out)["tabelas"] for f in t["arquivos"]]  # type: ignore[attr-defined]


def _later(monkeypatch: pytest.MonkeyPatch, settings: Settings, month: str) -> None:
    monkeypatch.setattr(lake, "utcnow", lambda: datetime.fromisoformat(f"{month}-05T00:00:00+00:00"))
    export.export(settings)


def test_retention_removes_the_parquet_of_a_version_older_than_the_window_and_marks_its_manifest(
    monkeypatch: pytest.MonkeyPatch, con: Connection, settings: Settings
) -> None:
    out, folder, old_file = _old_version(monkeypatch, con, settings, "2025-10")
    before = json.loads((folder / "manifesto.json").read_text())
    _later(monkeypatch, settings, "2026-11")  # 13 meses depois
    assert not old_file.exists() and all(f.exists() for f in _cited(out))  # o citado pelo atual fica
    after = json.loads((folder / "manifesto.json").read_text())
    assert after.pop("arquivos_removidos") and after == before  # segue descrevendo e dando o hash
    assert (folder / "catalogo.duckdb").exists() and (folder / "datapackage.json").exists()


def test_retention_keeps_a_version_inside_the_window(
    monkeypatch: pytest.MonkeyPatch, con: Connection, settings: Settings
) -> None:
    out, folder, old_file = _old_version(monkeypatch, con, settings, "2025-11")
    _later(monkeypatch, settings, "2026-11")  # 12 meses: ainda dentro
    assert old_file.exists() and "arquivos_removidos" not in json.loads(
        (folder / "manifesto.json").read_text()
    )
    monkeypatch.setenv("DADO_PUBLICO_VERSOES_MESES", "6")  # a janela é configurável
    _later(monkeypatch, settings, "2026-11")
    assert not old_file.exists()


def test_a_pinned_version_keeps_its_parquet_forever(
    monkeypatch: pytest.MonkeyPatch, con: Connection, settings: Settings
) -> None:
    out, folder, old_file = _old_version(monkeypatch, con, settings, "2025-10")
    lake.fix(lake.connect(settings, warehouse_file=False), lake.location(settings), "2025-10", "10.5281/x")
    assert json.loads((folder / "fixada.json").read_text())["doi"] == "10.5281/x"
    _later(monkeypatch, settings, "2030-01")
    assert old_file.exists() and "arquivos_removidos" not in json.loads(
        (folder / "manifesto.json").read_text()
    )
    with pytest.raises(ValueError, match="não existe"):
        lake.fix(lake.connect(settings, warehouse_file=False), lake.location(settings), "2020-01", "x")


def test_a_run_that_fails_midway_through_the_retention_deletes_nothing_cited(
    monkeypatch: pytest.MonkeyPatch, con: Connection, settings: Settings
) -> None:
    out, folder, old_file = _old_version(monkeypatch, con, settings, "2025-10")
    monkeypatch.setattr(lake, "delete_orphans", lambda *a: (_ for _ in ()).throw(RuntimeError("caiu")))
    with pytest.raises(RuntimeError):
        _later(monkeypatch, settings, "2026-11")
    assert (
        all(f.exists() for f in _cited(out))
        and "arquivos_removidos" not in (folder / "manifesto.json").read_text()
    )
    monkeypatch.undo()  # a rodada seguinte refaz a retenção
    monkeypatch.setattr(lake, "utcnow", lambda: datetime.fromisoformat("2026-11-06T00:00:00+00:00"))
    export.export(settings)
    assert not old_file.exists() and all(f.exists() for f in _cited(out))
