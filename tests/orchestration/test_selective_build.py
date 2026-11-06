"""ADR 0047, equivalência: uma sequência de noites no modo seletivo termina com as mesmas tabelas que uma
reconstrução completa (contagem e soma do hash das linhas, por tabela), no pipeline sintético."""

import shutil
from datetime import date
from pathlib import Path
from typing import Any

import pytest

from dado_publico_brasil.core import migrations, runs
from dado_publico_brasil.core.settings import Settings
from dado_publico_brasil.core.warehouse import Connection, scalar
from dado_publico_brasil.transformation import build, dbt, selection

MONDAY = date(2026, 11, 9)
LAYERS = ("staging", "intermediate", "marts")
PREFIX = "model.dado_publico_brasil."


def fingerprints(con: Connection) -> dict[str, tuple[int, int]]:
    """(linhas, soma do hash) de toda tabela e view das camadas do dbt."""
    marks = ",".join("?" * len(LAYERS))
    found = con.execute(
        "SELECT schema_name, table_name FROM duckdb_tables() "
        f"WHERE database_name = current_database() AND schema_name IN ({marks}) "
        "UNION SELECT schema_name, view_name FROM duckdb_views() "
        f"WHERE database_name = current_database() AND NOT internal AND schema_name IN ({marks})",
        (*LAYERS, *LAYERS),
    ).fetchall()
    out = {}
    for schema, table in sorted(found):
        n, h = con.execute(
            f'SELECT count(*), coalesce(sum(hash(t)::HUGEINT), 0) FROM {schema}."{table}" t'
        ).fetchone()  # type: ignore[misc]
        out[f"{schema}.{table}"] = (n, int(h))
    return out


def models_of_last_night(settings: Settings) -> set[str]:
    """Modelos que a última execução de cada fase do dbt construiu, pelos nomes."""
    con = migrations.open_warehouse(settings)
    try:
        rows = con.execute(
            "SELECT id_no FROM metadata.testes_resultados WHERE tipo = 'model' AND id_execucao IN "
            "(SELECT max(id_execucao) FROM metadata.execucoes WHERE fonte = 'dbt' GROUP BY etapa)"
        ).fetchall()
    finally:
        con.close()
    return {r[0].removeprefix(PREFIX) for r in rows}


def sql(settings: Settings, statement: str, params: tuple[str, ...] = ()) -> None:
    con = migrations.open_warehouse(settings)
    con.execute(statement, params)
    con.close()


def test_selective_nights_end_with_the_same_tables_as_a_complete_rebuild(
    snapshots: dict[str, Path], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(runs, "code_version", lambda: "teste")  # a árvore suja sempre reconstrói tudo
    original = selection.plan
    monkeypatch.setattr(
        selection,
        "plan",
        lambda con, s, stage, today=None, force=False: original(con, s, stage, MONDAY, force),
    )  # segunda-feira: sem a reconstrução dominical
    calls: list[tuple[str, ...]] = []
    invoke = dbt.invoke

    def spy(settings: Settings, *args: str, **kw: Any) -> dbt.Outcome:
        calls.append(args)
        return invoke(settings, *args, **kw)

    monkeypatch.setattr(dbt, "invoke", spy)

    selective, complete = (Settings(storage_root=tmp_path / n) for n in ("seletivo", "completo"))
    both = (selective, complete)
    for settings in both:
        shutil.copytree(snapshots["full"], settings.storage_root)
        sql(settings, "UPDATE metadata.execucoes SET versao_commit = 'teste'")  # o código do snapshot
    con = migrations.open_warehouse(selective)
    assert scalar(con, "SELECT count(*) FROM metadata.execucoes WHERE fl_completa") == 2
    con.close()  # o snapshot tem uma reconstrução completa de cada fase

    # noite 0: nada novo, o dbt nem é chamado
    build.run(selective)
    assert calls == []

    # noite 1: dado novo só da Câmara (captura carregada depois da última construção)
    for settings in both:
        sql(settings, "UPDATE raw_federal_camara.deputados SET municipio_nascimento = 'cidade nova'")
        sql(
            settings,
            "UPDATE metadata.capturas SET dt_carga = ? WHERE fonte = 'camara' AND dataset = 'deputados'",
            (runs.now(),),
        )
    build.run(selective)
    ran = models_of_last_night(selective)
    assert {"stg_camara__deputados", "dim_pessoas_cadastro"} <= ran
    assert not {m for m in ran if m.startswith("stg_tse__")}  # o TSE não mudou: nenhum ramo dele

    # noite 2: a identidade muda (um identificador perde a pessoa e ganha outra)
    for settings in both:
        sql(
            settings,
            "DELETE FROM identity.pessoas_identificadores WHERE (fonte, id_tipo, id_na_fonte) = ("
            "SELECT fonte, id_tipo, id_na_fonte FROM identity.pessoas_identificadores "
            "WHERE fonte = 'camara' ORDER BY id_na_fonte LIMIT 1)",
        )
    build.run(selective)
    ran = models_of_last_night(selective)
    assert {"stg_identity__pessoas_identificadores", "dim_pessoas"} <= ran
    assert not {m for m in ran if m.startswith(("stg_camara__", "stg_tse__"))}

    # noite 3: um modelo falhou na noite anterior (e a tabela ficou errada): é refeito
    for settings in both:
        sql(settings, "DELETE FROM marts.dim_legislaturas")
    sql(
        selective,
        "UPDATE metadata.testes_resultados SET resultado = 'error' WHERE id_no = ? AND id_execucao = "
        "(SELECT max(id_execucao) FROM metadata.testes_resultados WHERE id_no = ?)",
        (PREFIX + "dim_legislaturas",) * 2,
    )
    build.run(selective)
    ran = models_of_last_night(selective)
    assert "dim_legislaturas" in ran and "stg_identity__pessoas" not in ran

    # o completo recebeu as mesmas alterações e refaz tudo uma vez
    build.run(complete, full=True)
    results = {}
    for name, settings in (("seletivo", selective), ("completo", complete)):
        con = migrations.open_warehouse(settings)
        results[name] = fingerprints(con)
        con.close()
    assert results["seletivo"].keys() == results["completo"].keys()
    assert [t for t in results["seletivo"] if results["seletivo"][t] != results["completo"][t]] == []
