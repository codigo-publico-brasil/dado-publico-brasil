"""Linha de comando da camada de dados (a mesma lógica que o Dagster executa).

A pasta de armazenamento e o warehouse vêm de DADO_PUBLICO_STORAGE_ROOT e DADO_PUBLICO_WAREHOUSE (ou de
--storage-root e --warehouse, que vencem). Tudo roda a partir da pasta dado-publico-brasil:

    uv run dado-publico run --incremental
    uv run dado-publico run --historical --from-year 2000
    uv run dado-publico run --incremental --source senado
    uv run dado-publico run --years 2024 2025 2026 --extra-years 2019

Etapas separadas: extract, load [--rebuild], transform, identity, catalog, docs, query --sql "SELECT ...".
Publicação: publish copia os marts para o PostgreSQL de serviço (DADO_PUBLICO_POSTGRES_DSN).
Auditoria: verify (hashes do landing e cópia da identidade) e coverage (itens obtidos nos datasets por item).
Observabilidade: observe resume a saúde dos dados (fontes, carga, testes, anomalias) e falha se houver
problema; --email envia o relatório e --html gera o do Elementary (anexo, se houver --email).
Datasets por item (tramitação, processos): `--foreach 200` busca os 200 mais recentes que faltam;
`--foreach all` busca todos; `--dataset NOME` limita a um dataset (também nos anuais,
como `--years 2022 --dataset votacao`).
Modos de extração: --years (anos pedidos), --historical --from-year N (carga massiva) e
--incremental (a execução diária: só a partição em curso dos datasets que a fonte atualiza todo dia).
"""

import argparse
from pathlib import Path

from dado_publico_brasil.core import alert, migrations, warehouse
from dado_publico_brasil.core import settings as settings_module
from dado_publico_brasil.core.settings import Settings
from dado_publico_brasil.ingestion import contract, foreach, landing, loader
from dado_publico_brasil.orchestration import pipeline
from dado_publico_brasil.transformation import build, catalog, dbt, observability, publish, snapshot

COMMANDS = (
    "run",
    "extract",
    "load",
    "transform",
    "identity",
    "publish",
    "catalog",
    "docs",
    "query",
    "verify",
    "coverage",
    "observe",
)


def _plan(args: argparse.Namespace) -> pipeline.Plan:
    def plan(source: contract.SourceContract) -> list[landing.Item]:
        if args.incremental:
            items = landing.plan_incremental(source)
        elif args.historical:
            items = landing.plan_historical(source, args.from_year, args.to_year, args.extra_years)
        else:
            items = landing.plan(source, args.years, args.extra_years)
        # `--dataset` limita a extração a um dataset (os pesados, como os votos do TSE, vão por ano)
        return [item for item in items if args.dataset in (None, item[0])]

    return plan


def _per_item(args: argparse.Namespace) -> int:
    return foreach.MAX if args.foreach == "all" else int(args.foreach)


def _query(settings: Settings, sql: str) -> None:
    con = warehouse.connect(settings, read_only=True)
    try:
        result = con.execute(sql)
        names = [d[0] for d in result.description]
        rows = [["" if v is None else str(v) for v in r] for r in result.fetchmany(200)]
    finally:
        con.close()
    widths = [max(len(n), *(len(r[i]) for r in rows), 1) for i, n in enumerate(names)]
    print("  ".join(n.ljust(w) for n, w in zip(names, widths, strict=True)))
    print("  ".join("-" * w for w in widths))
    for row in rows:
        print("  ".join(v.ljust(w) for v, w in zip(row, widths, strict=True)))


def _coverage(settings: Settings, only: str | None) -> None:
    con = warehouse.connect(settings, read_only=True)
    try:
        for source in contract.find_all():
            for name, dataset in source.datasets.items():
                if dataset.foreach and only in (None, source.source):
                    counts = foreach.coverage(con, source, name)
                    print(f"{source.source}.{name}: " + ", ".join(f"{k} {v}" for k, v in counts.items()))
    finally:
        con.close()


def _ingest(settings: Settings, args: argparse.Namespace) -> None:
    con = migrations.open_warehouse(settings)
    try:
        for source in contract.find_all():
            if args.source in (None, source.source):
                if args.command == "extract":
                    n = landing.extract_plan(con, settings, source, _plan(args)(source), force=args.force)
                    print(f"{source.source}: {n} datasets processados")
                    for name, dataset in source.datasets.items():
                        if dataset.foreach and args.foreach and args.dataset in (None, name):
                            foreach.capture(con, settings, source, name, _per_item(args))
                else:
                    captures, rows = loader.load_pending(con, settings, source, args.rebuild, args.dataset)
                    print(f"{source.source}: {captures} capturas carregadas, {rows} linhas")
    finally:
        con.close()


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument("command", choices=COMMANDS)
    p.add_argument(
        "--foreach", help="itens por dataset por item (número ou all); sem isso, esses datasets não rodam"
    )
    p.add_argument("--dataset", help="só este dataset (anual, único ou, com --foreach, por item)")
    p.add_argument("--source", help="só esta fonte (padrão: todas as de sources/)")
    p.add_argument("--years", type=int, nargs="+", default=[], help="anos de votações e proposições")
    p.add_argument("--extra-years", type=int, nargs="*", default=[], help="anos só de proposições")
    p.add_argument("--historical", action="store_true", help="carga massiva de um intervalo de anos")
    p.add_argument("--from-year", type=int, help="primeiro ano do histórico")
    p.add_argument("--to-year", type=int, help="último ano do histórico (padrão: o ano corrente)")
    p.add_argument(
        "--incremental", action="store_true", help="só a partição em curso das fontes com `schedule`"
    )
    p.add_argument("--force", action="store_true", help="baixa mesmo que a fonte diga que não mudou")
    p.add_argument("--rebuild", action="store_true", help="carrega tudo de novo no raw")
    p.add_argument("--email", action="store_true", help="envia o relatório do comando observe por e-mail")
    p.add_argument("--html", action="store_true", help="gera o relatório HTML do Elementary (observe)")
    p.add_argument("--sql", help="consulta para o comando query (somente leitura)")
    p.add_argument("--output", type=Path, help="arquivo de saída do comando catalog")
    p.add_argument("--port", type=int, default=8080, help="porta do comando docs")
    p.add_argument("--storage-root", type=Path, help="pasta de armazenamento (padrão: settings.yml)")
    p.add_argument("--warehouse", help="arquivo do warehouse (padrão: settings.yml)")
    args = p.parse_args(argv)

    if args.command in ("run", "extract") and sum([bool(args.years), args.historical, args.incremental]) != 1:
        p.error("escolha um modo de extração: --years, --historical ou --incremental")
    if args.historical and args.from_year is None:
        p.error("--historical exige --from-year")
    if args.command == "query" and not args.sql:
        p.error("query exige --sql")

    settings = settings_module.load_settings(storage_root=args.storage_root, warehouse=args.warehouse)
    match args.command:
        case "query":
            _query(settings, args.sql)
        case "catalog":
            output = args.output or Path("docs/03-consultar/01-catalogo.md")
            output.write_text(catalog.markdown(settings), encoding="utf-8")
            print(f"Catálogo escrito em {output}")
        case "docs":
            return dbt.serve_docs(settings, args.port)
        case "run":
            print(
                pipeline.run_all(
                    settings,
                    _plan(args),
                    args.rebuild,
                    args.force,
                    only=args.source,
                    per_item=_per_item(args) if args.foreach else None,
                    dataset_name=args.dataset,
                )
            )
        case "transform":
            build.run(settings)
            print("dbt concluído (staging, intermediate, identidade e marts)")
        case "verify":
            con = migrations.open_warehouse(settings)
            problems = foreach.verify(con, settings, args.source) + snapshot.problems(con, settings)
            con.close()
            print(chr(10).join(problems) or "landing íntegro: todos os hashes conferem")
            return 1 if problems else 0
        case "observe":
            con = warehouse.connect(settings, read_only=True)
            lines, failed = observability.report(con)
            con.close()
            print(chr(10).join(lines))
            html = observability.html_report(settings) if args.html else None
            if html:
                print(f"Relatório HTML do Elementary: {html}")
            if args.email:
                sent = alert.send("Plataforma de dados: relatório", chr(10).join(lines), html)
                print("e-mail enviado" if sent else "SMTP não configurado")
            return 1 if failed else 0
        case "coverage":
            _coverage(settings, args.source)
        case "identity":
            print(f"{build.resolve_identity(settings)} pessoas novas")
        case "publish":
            published = publish.publish(settings)
            print(f"{len(published)} marts publicados ({sum(published.values())} linhas)")
        case _:
            _ingest(settings, args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
