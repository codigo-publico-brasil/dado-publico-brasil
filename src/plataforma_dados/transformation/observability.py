"""Observabilidade dos dados (ADR 0018): o que mudou de uma execução para a outra, sem um teste por caso.

Cada execução tira uma fotografia de todas as tabelas (linhas e colunas; nos marts, também a proporção de
nulos e os valores distintos de cada coluna) em `metadata.table_profile` e `metadata.column_profile`. A
comparação com a fotografia anterior grava achados em `metadata.data_checks` (`ok`, `warn` ou `error`): tabela
que sumiu, volume que despencou ou explodiu (uma junção que multiplica linhas), coluna nova ou removida, nulos
que aumentaram, valores distintos que colapsaram. Pega problema de lógica da transformação, mudança de formato
da origem e perda na carga sem que alguém tenha previsto o caso. Nada aqui interrompe o pipeline:
`plataforma observe` resume e falha (código de saída 1) se houver erro.
"""

from plataforma_dados.core import runs, warehouse
from plataforma_dados.core.warehouse import Connection

SHRINK_WARN, SHRINK_ERROR, GROWTH_WARN = 0.8, 0.5, 2.0  # linhas de hoje sobre as da execução anterior
MIN_ROWS = 50  # abaixo disso a variação relativa não diz nada
NULL_WARN, NULL_ERROR = 0.10, 0.30  # aumento da proporção de nulos de uma coluna dos marts
DISTINCT_DROP = 0.5
PROFILED = ("marts",)  # camadas com perfil de coluna: o contrato com as aplicações

TABLES = (
    "SELECT table_schema, table_name FROM information_schema.tables "
    "WHERE table_schema NOT IN ('metadata', 'information_schema', 'pg_catalog') "
    "AND table_schema NOT LIKE 'dlt\\_tmp\\_%' ESCAPE '\\' AND table_name NOT LIKE '\\_dlt\\_%' ESCAPE '\\' "
    "ORDER BY 1, 2"
)
COLUMNS = (
    "SELECT column_name, data_type FROM information_schema.columns "
    "WHERE table_schema = ? AND table_name = ? AND column_name NOT LIKE '\\_dlt\\_%' ESCAPE '\\' "
    "ORDER BY ordinal_position"
)
INSERT_CHECK = (
    "INSERT INTO metadata.data_checks "
    "(run_id, checked_at, schema_name, table_name, column_name, check_name, status, detail) "
    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
)
TABLE_ROWS = "SELECT schema_name, table_name, row_count FROM metadata.table_profile WHERE run_id = ?"
COLUMN_STATS = (
    "SELECT schema_name, table_name, column_name, null_rate, distinct_values "
    "FROM metadata.column_profile WHERE run_id = ?"
)


def profile(con: Connection, run_id: int) -> int:
    """Grava a fotografia da execução. Devolve quantas tabelas foram fotografadas."""
    tables = con.execute(TABLES).fetchall()
    for schema, table in tables:
        cols = con.execute(COLUMNS, (schema, table)).fetchall()
        if schema in PROFILED:
            exprs = ", ".join(f'count("{c}"), approx_count_distinct("{c}")' for c, _ in cols)
            row = con.execute(f"SELECT count(*), {exprs} FROM {schema}.{table}").fetchone()
            assert row is not None
            rows = int(row[0])
            stats: list[tuple[float | None, int | None]] = [
                ((1 - row[1 + 2 * i] / rows) if rows else 0.0, int(row[2 + 2 * i])) for i in range(len(cols))
            ]
        else:
            rows = int(warehouse.scalar(con, f"SELECT count(*) FROM {schema}.{table}"))
            stats = [(None, None)] * len(cols)
        con.execute("INSERT INTO metadata.table_profile VALUES (?, ?, ?, ?)", (run_id, schema, table, rows))
        con.executemany(
            "INSERT INTO metadata.column_profile VALUES (?, ?, ?, ?, ?, ?, ?)",
            [
                (run_id, schema, table, name, kind, nulls, distinct)
                for (name, kind), (nulls, distinct) in zip(cols, stats, strict=True)
            ],
        )
    return len(tables)


def _check(
    con: Connection,
    run_id: int,
    status: str,
    name: str,
    where: tuple[str | None, str | None, str | None],
    detail: str,
) -> None:
    con.execute(INSERT_CHECK, (run_id, runs.now(), *where, name, status, detail))


def compare(con: Connection, run_id: int) -> int:
    """Compara a fotografia da execução com a anterior e grava os achados. Devolve quantos não são `ok`."""
    previous = warehouse.scalar(
        con, "SELECT max(run_id) FROM metadata.table_profile WHERE run_id < ?", (run_id,)
    )
    if previous is None:
        _check(con, run_id, "ok", "primeira_fotografia", (None, None, None), "não há execução anterior")
        return 0
    before = {(s, t): n for s, t, n in con.execute(TABLE_ROWS, (previous,)).fetchall()}
    now = {(s, t): n for s, t, n in con.execute(TABLE_ROWS, (run_id,)).fetchall()}
    for s, t in sorted(before.keys() - now.keys()):
        _check(con, run_id, "error", "tabela_sumiu", (s, t, None), f"tinha {before[s, t]} linhas antes")
    for s, t in sorted(now.keys() - before.keys()):
        _check(con, run_id, "ok", "tabela_nova", (s, t, None), f"{now[s, t]} linhas")
    for s, t in sorted(now.keys() & before.keys()):
        was, is_ = before[s, t], now[s, t]
        detail = f"de {was} para {is_} linhas"
        if was < MIN_ROWS:
            continue
        if is_ < SHRINK_ERROR * was:
            _check(con, run_id, "error", "volume_caiu", (s, t, None), detail)
        elif is_ < SHRINK_WARN * was:
            _check(con, run_id, "warn", "volume_caiu", (s, t, None), detail)
        elif is_ > GROWTH_WARN * was:
            _check(con, run_id, "warn", "volume_explodiu", (s, t, None), detail)
    _compare_columns(con, run_id, previous)
    sql = "SELECT count(*) FROM metadata.data_checks WHERE run_id = ? AND status <> 'ok'"
    return int(warehouse.scalar(con, sql, (run_id,)))


def _compare_columns(con: Connection, run_id: int, previous: int) -> None:
    before = {(s, t, c): (n, d) for s, t, c, n, d in con.execute(COLUMN_STATS, (previous,)).fetchall()}
    now = {(s, t, c): (n, d) for s, t, c, n, d in con.execute(COLUMN_STATS, (run_id,)).fetchall()}
    tables_before = {(s, t) for s, t, _ in before}
    tables_now = {(s, t) for s, t, _ in now}
    for s, t, c in sorted(before.keys() - now.keys()):
        if (s, t) in tables_now:
            status = "error" if s in PROFILED else "warn"
            _check(con, run_id, status, "coluna_removida", (s, t, c), "a coluna existia na execução anterior")
    for s, t, c in sorted(now.keys() - before.keys()):
        if (s, t) in tables_before:
            _check(con, run_id, "ok", "coluna_nova", (s, t, c), "a coluna não existia na execução anterior")
    for key in sorted(now.keys() & before.keys()):
        (null_now, distinct_now), (null_was, distinct_was) = now[key], before[key]
        if null_now is None or null_was is None:
            continue
        detail = f"de {null_was:.1%} para {null_now:.1%} de linhas vazias"
        if null_now - null_was >= NULL_ERROR:
            _check(con, run_id, "error", "nulos_aumentaram", key, detail)
        elif null_now - null_was >= NULL_WARN:
            _check(con, run_id, "warn", "nulos_aumentaram", key, detail)
        if distinct_was and distinct_was >= 20 and distinct_now is not None:
            if distinct_now < DISTINCT_DROP * distinct_was:
                detail = f"de {distinct_was} para {distinct_now} valores distintos"
                _check(con, run_id, "warn", "valores_distintos_cairam", key, detail)


def run(con: Connection, run_id: int) -> int:
    """Fotografa e compara. Devolve quantos achados não são `ok`."""
    profile(con, run_id)
    return compare(con, run_id)


def report(con: Connection) -> tuple[list[str], bool]:
    """O resumo da última execução fotografada: achados, erros das fontes e da carga, e testes do dbt.

    Devolve (linhas do relatório, há erro?).
    """
    latest = warehouse.scalar(con, "SELECT max(run_id) FROM metadata.table_profile")
    if latest is None:
        return ["Nenhuma execução fotografada ainda: rode `plataforma transform`."], False
    when = warehouse.scalar(con, "SELECT started_at FROM metadata.runs WHERE id = ?", (latest,))
    lines = [f"Execução {latest} ({when})", ""]
    checks = con.execute(
        "SELECT status, check_name, schema_name || '.' || table_name, column_name, detail "
        "FROM metadata.data_checks WHERE run_id = ? AND status <> 'ok' ORDER BY status DESC, check_name, 3",
        (latest,),
    ).fetchall()
    errors = sum(1 for c in checks if c[0] == "error")
    lines.append(f"Comparação com a execução anterior: {errors} erros, {len(checks) - errors} avisos")
    for status, name, table, column, detail in checks:
        lines.append(f"  [{status}] {name}: {table}{'.' + column if column else ''}: {detail}")
    sources = con.execute(
        "SELECT status, source || '.' || dataset, check_name, detail, count(*), "
        "min(partition), max(partition) FROM metadata.source_checks WHERE status <> 'ok' AND id IN "
        "(SELECT max(id) FROM metadata.source_checks GROUP BY source, dataset, partition, check_name) "
        "GROUP BY ALL ORDER BY status DESC, 2, 3"
    ).fetchall()
    source_errors = sum(n for status, *_, n, _, _ in sources if status == "error")
    total = sum(n for *_, n, _, _ in sources)
    lines += [
        "",
        f"Fontes e carga (última verificação): {source_errors} erros, {total - source_errors} avisos",
    ]
    for status, name, check, detail, n, first, last in sources:
        years = (
            f" ({first} a {last})"
            if first is not None and first != last
            else (f" ({first})" if first else "")
        )
        lines.append(
            f"  [{status}] {name} ({check}): {detail}: {n} partições{years}"
            if n > 1
            else f"  [{status}] {name} ({check}): {detail}{years}"
        )
    failing = con.execute(
        "SELECT status, unique_id, failures FROM metadata.dbt_results "
        "WHERE run_id = (SELECT max(run_id) FROM metadata.dbt_results) "
        "AND status IN ('error', 'fail') ORDER BY 2"
    ).fetchall()
    lines += ["", f"Testes do dbt do último build: {len(failing)} reprovados"]
    lines += [f"  [{s}] {uid} ({n})" for s, uid, n in failing]
    return lines, bool(errors or source_errors or failing)
