"""Export do lake público (ADR 0035): Parquet fiel ao warehouse, idempotente, com catálogo e descrições.

Usa um warehouse pequeno montado aqui (rápido); o destino é a pasta local, o mesmo código do R2 menos o
segredo. O que depende de credencial real (COPY, LIST e DELETE em `r2://` e o PUT do catálogo) não é testado aqui.
"""

import base64
import hashlib
import http.client
import json
import mimetypes
import shutil
import threading
import time
import zipfile
from pathlib import Path

import duckdb
import pytest

from dado_publico_brasil.core.settings import Settings
from dado_publico_brasil.core.warehouse import Connection, scalar
from dado_publico_brasil.ingestion import arquivos, landing
from dado_publico_brasil.ingestion import contract as contracts
from dado_publico_brasil.transformation import dbt, export, observability

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
    con.execute("CREATE VIEW marts.app_visao AS SELECT 1 AS a")
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
    con: Connection, settings: Settings, max_bytes: int = export.MAX_BYTES
) -> tuple[Path, dict[str, int]]:
    build(con, settings)
    con.close()  # o export abre o warehouse só para leitura
    result = export.export(settings, max_bytes=max_bytes)
    return settings.storage_root / "lake", result


def change(settings: Settings, sql: str) -> None:
    live = duckdb.connect(str(settings.warehouse))
    live.execute(sql)
    live.close()


def manifest(out: Path) -> dict[str, list[dict[str, object]]]:
    return json.loads((out / "manifesto.json").read_text(encoding="utf-8"))  # type: ignore[no-any-return]


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
    }
    assert result["tabelas"] == len(tables) and result["gravadas"] == len(tables)
    live = duckdb.connect(str(settings.warehouse), read_only=True)
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
    assert export.verify(settings) == []


def test_a_changed_table_alone_is_rewritten_and_verify_catches_tampering(
    con: Connection, settings: Settings
) -> None:
    out, _ = run(con, settings)
    change(settings, "INSERT INTO staging.stg_camara__base VALUES (999, 'novo')")
    assert export.export(settings)["gravadas"] == 2  # a tabela e a view que a lê
    (out / f"{VOTOS}.parquet").write_bytes(b"adulterado")
    assert export.verify(settings) == [f"{VOTOS}.parquet difere do manifesto"]


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
    assert not [t for t in tables if str(t["tabela"]).startswith(("app_", "stg_identity", "stg_metadata"))]


def test_a_big_table_with_a_partition_is_split_by_year_and_filters_by_it(
    con: Connection, settings: Settings
) -> None:
    out, _ = run(con, settings, max_bytes=1)
    split = votos(out)
    names = sorted(f["arquivo"] for f in split["arquivos"])  # type: ignore[attr-defined]
    assert names == [f"{VOTOS}/ano={y}/part-0.parquet" for y in (2020, 2021, 2022)]
    assert split["particao"] == "year(dt_voto)" and split["ano"] == [2020, 2021, 2022]
    assert split["colunas"][-1]["nome"] == "ano"  # type: ignore[index]
    assert sum(f["linhas"] for f in split["arquivos"]) == 1000  # type: ignore[attr-defined]
    assert export.verify(settings) == []
    cat = duckdb.connect(str(out / "catalogo.duckdb"), read_only=True)
    live = duckdb.connect(str(settings.warehouse), read_only=True)
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
    assert [f["arquivo"] for f in split["arquivos"]] == [f"{VOTOS}.parquet"]  # type: ignore[attr-defined]
    assert split["particao"] == "year(dt_voto)" and split["ano"] is None
    mem = duckdb.connect()
    years = [
        r[0]
        for r in mem.execute(f"SELECT year(dt_voto) FROM '{(out / VOTOS).as_posix()}.parquet'").fetchall()
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
    change(settings, "INSERT INTO marts.fct_votos VALUES (5000, DATE '2021-01-01', 'x', 1)")
    result = export.export(settings, max_bytes=1)  # de arquivo único para partição
    assert result["orfaos"] == 1 and not (out / f"{VOTOS}.parquet").exists()
    change(settings, "INSERT INTO marts.fct_votos VALUES (5001, DATE '2021-01-01', 'x', 1)")
    change(settings, "DROP VIEW staging.stg_camara__visao")
    result = export.export(settings, prune=True)  # de partição para arquivo único, e uma tabela removida
    assert result["orfaos"] == 3 + 1
    listed = {p.relative_to(out).as_posix() for p in out.rglob("*.parquet")}
    assert listed == {f["arquivo"] for t in manifest(out)["tabelas"] for f in t["arquivos"]}  # type: ignore[attr-defined]
    assert export.verify(settings) == []


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


@pytest.mark.parametrize("max_bytes", [export.MAX_BYTES, 1])
def test_the_parquet_carries_the_table_and_column_descriptions(
    con: Connection, settings: Settings, max_bytes: int
) -> None:
    out, _ = run(con, settings, max_bytes=max_bytes)
    live = duckdb.connect(str(settings.warehouse), read_only=True)
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
    meta = kv(out / f"{VOTOS}.parquet")
    assert json.loads(meta["descricoes_colunas"])["qtd"] == "Outra descrição."


def test_huge_descriptions_are_cut_with_a_warning(con: Connection, settings: Settings) -> None:
    build(con, settings)
    con.execute(f"COMMENT ON COLUMN marts.fct_votos.qtd IS '{'x' * (export.MAX_KV_BYTES + 10)}'")
    con.close()
    with pytest.warns(UserWarning, match="descricoes_colunas"):
        export.export(settings)
    meta = kv(settings.storage_root / "lake" / f"{VOTOS}.parquet")
    assert len(meta["descricoes_colunas"].encode()) <= export.MAX_KV_BYTES


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
    assert export._domain({}, "dim_pessoas") == "pessoas"


def test_publish_docs_uploads_both_pages_as_html_and_does_nothing_without_r2(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, settings: Settings
) -> None:
    sent: list[tuple[str, str | None]] = []
    page = tmp_path / "p.html"
    page.write_text("<html></html>")
    monkeypatch.setattr(dbt, "static_docs", lambda s: page)
    monkeypatch.setattr(observability, "html_report", lambda s: page)
    monkeypatch.setattr(
        export, "r2_request", lambda m, key, path=None, content_type=None: sent.append((key, content_type))
    )
    monkeypatch.setattr(export, "_index", lambda s: page)
    monkeypatch.setattr(export, "_r2", lambda: {})
    assert export.publish_docs(settings) == [] and sent == []
    monkeypatch.setattr(export, "_r2", lambda: {"BUCKET": "b"})
    assert export.publish_docs(settings) == ["docs/dbt.html", "docs/qualidade.html", "docs/index.html"]
    assert sent == [
        ("docs/dbt.html", "text/html; charset=utf-8"),
        ("docs/qualidade.html", "text/html; charset=utf-8"),
        ("docs/index.html", "text/html; charset=utf-8"),
    ]


def test_the_home_page_fills_the_card_from_the_published_manifest(
    con: Connection, settings: Settings
) -> None:
    out, _ = run(con, settings)
    html = export._index(settings).read_text(encoding="utf-8")
    published = manifest(out)
    assert "{{" not in html
    assert str(published["id_execucao"]) in html and f">{len(published['tabelas'])}<" in html


def test_seed_mart_goes_to_the_reference_folder() -> None:
    assert export._key({}, "marts", "dim_cargos") == "marts/referencia/dim_cargos"


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
    cur = c.execute(f"SELECT * FROM read_parquet('{(out / folder).as_posix()}.parquet') ORDER BY caminho")
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
        {"FRJ1001_div.jpg": b"\xff\xd8nova"},
    )
    assert arquivos.materialize(con, settings, contracts.find("tse")) == 1  # nova captura, mesmo caminho
    assert (base / "judiciario/federal/tse/arq_fotos" / FOTO_LOCAL).read_bytes() == b"\xff\xd8nova"


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
    assert kv(out / f"{FOTOS}.parquet")["descricao"]
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
    assert again["gravadas"] == 0 and sent == [
        (out / "catalogo.duckdb").as_posix()
    ]  # nenhum arquivo reenviado
    monkeypatch.undo()
    assert (out / FOTOS / FOTO_LOCAL).stat().st_mtime_ns == stamp
    assert export.verify(settings) == []
    nova = b"\xff\xd8nova"
    con = duckdb.connect(str(settings.warehouse))
    capture(con, settings, "tse", "fotos_rj", 2022, "fotos_rj-ba9876543210.zip", {"FRJ1001_div.jpg": nova})
    arquivos.materialize(con, settings, contracts.find("tse"))
    con.close()
    export.export(settings)
    assert (out / FOTOS / FOTO_LOCAL).read_bytes() == nova and export.verify(settings) == []
    (out / FOTOS / FOTO_LOCAL).write_bytes(b"adulterada")
    (out / FOTOS / "2022/RJ/solta.jpg").write_bytes(b"x")
    assert sorted(export.verify(settings)) == [
        f"{FOTOS}/2022/RJ/1001.jpg difere do controle",
        f"{FOTOS}/2022/RJ/solta.jpg fora do controle",
    ]
    (out / DOU / "secao1/202608/base.zip").unlink()
    assert f"falta {DOU}/secao1/202608/base.zip" in export.verify(settings)


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
    monkeypatch.setattr(export, "_published", lambda dataset: False)
    with pytest.raises(ValueError, match="--prune"):
        export.export(settings)
    assert (out / FOTOS / FOTO_LOCAL).exists() and (out / DOU / "secao1/202608/base.zip").exists()
    export.export(settings, prune=True)
    assert not (out / FOTOS / FOTO_LOCAL).exists()
    assert {t["tabela"] for t in manifest(out)["tabelas"]}.isdisjoint({"arq_fotos", "arq_secoes"})


def test_publicar_only_counts_when_it_is_exactly_true() -> None:
    assert export._published({"arquivos": {"publicar": True}})
    assert not any(export._published({"arquivos": {"publicar": v}}) for v in ("false", "sim", 1, None))
    assert not export._published({}) and not export._published({"arquivos": None})


def test_the_signed_upload_carries_content_type_cache_control_and_checksum(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    seen: dict[str, str] = {}

    class Response:
        status = 200

        def read(self) -> bytes:
            return b""

    class Conn:
        def __init__(self, host: str, timeout: int) -> None: ...

        def request(self, method: str, uri: str, body: object, headers: dict[str, str]) -> None:
            seen.update({k.lower(): v for k, v in headers.items()})

        def getresponse(self) -> Response:
            return Response()

        def close(self) -> None: ...

    keys = ("ACCOUNT_ID", "ACCESS_KEY_ID", "SECRET_ACCESS_KEY", "BUCKET")
    monkeypatch.setattr(export, "_r2", lambda: dict.fromkeys(keys, "x"))
    monkeypatch.setattr(http.client, "HTTPSConnection", Conn)
    monkeypatch.setattr(export, "_LOCAL", threading.local())
    file = tmp_path / "f.jpg"
    file.write_bytes(b"abc")
    export.r2_request("PUT", "k/f.jpg", file, "image/jpeg", {"Cache-Control": export.CACHE_CONTROL})
    assert seen["content-type"] == "image/jpeg" and seen["cache-control"] == export.CACHE_CONTROL
    assert seen["x-amz-checksum-sha256"] == base64.b64encode(hashlib.sha256(b"abc").digest()).decode()
    assert "cache-control" in seen["authorization"] and "x-amz-checksum-sha256" in seen["authorization"]


def test_a_transient_r2_error_is_retried(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    statuses = [500, 429, 200]

    class Response:
        def __init__(self) -> None:
            self.status = statuses.pop(0)

        def read(self) -> bytes:
            return b"erro"

    class Conn:
        def __init__(self, host: str, timeout: int) -> None: ...

        def request(self, method: str, uri: str, body: object, headers: dict[str, str]) -> None: ...

        def getresponse(self) -> Response:
            return Response()

        def close(self) -> None: ...

    keys = ("ACCOUNT_ID", "ACCESS_KEY_ID", "SECRET_ACCESS_KEY", "BUCKET")
    monkeypatch.setattr(export, "_r2", lambda: dict.fromkeys(keys, "x"))
    monkeypatch.setattr(http.client, "HTTPSConnection", Conn)
    monkeypatch.setattr(export, "_LOCAL", threading.local())
    monkeypatch.setattr(time, "sleep", lambda _: None)
    file = tmp_path / "f.jpg"
    file.write_bytes(b"abc")
    export.r2_request("PUT", "k/f.jpg", file, "image/jpeg")
    assert statuses == []  # duas falhas transitórias e a terceira tentativa passou

    statuses[:] = [403]
    with pytest.raises(RuntimeError, match="HTTP 403"):
        export.r2_request("PUT", "k/f.jpg", file, "image/jpeg")
