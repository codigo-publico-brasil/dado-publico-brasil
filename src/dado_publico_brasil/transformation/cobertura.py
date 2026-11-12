"""Cobertura e lacunas como documento (ADR 0054, item 4), gerado do warehouse: nenhum número é digitado à mão.

Lê só as medições das fontes (`marts.fct_fontes_ocorrencias`, `marts.agg_fontes_capturas`) e o resultado
dos testes de dado (`metadata.testes_resultados`). Sem nota nem ranking: a ordem é a da data ou a do nome.
"""

from typing import Any

from dado_publico_brasil.core.warehouse import Connection, rows, scalar

TITLE = "# Cobertura e lacunas"
INTRO = (
    "Para quem quer saber o que as fontes oficiais deixaram de entregar ao projeto e desde quando. Gerado de "
    "`marts/fontes/fct_fontes_ocorrencias`, `marts/fontes/agg_fontes_capturas` e "
    "`metadata/testes_resultados` (`dado-publico gaps`). Não edite à mão: o método é o SQL desses modelos e "
    "a descrição das colunas ([ADR 0054](../05-decisoes/0054-fato-agregado-e-avaliacao.md)). É medição da "
    "publicação das fontes, sem nota nem ranking; uma falha de rede do projeto pode aparecer como "
    "indisponibilidade da fonte (veja a descrição da tabela)."
)
LACUNAS = (
    "Testes do dbt que, no último resultado de cada um, avisaram ou falharam; a contagem é a de linhas que "
    "fazem o teste falhar (a lacuna)."
)
OPEN = (
    "SELECT * FROM marts.fct_fontes_ocorrencias WHERE fl_em_aberto "
    "ORDER BY dt_primeira_observacao, fonte, dataset, particao"
)
BY_TYPE = (
    "SELECT fonte, tipo_ocorrencia, count(*) AS qtd, count(*) FILTER (WHERE fl_em_aberto) AS abertas "
    "FROM marts.fct_fontes_ocorrencias GROUP BY ALL ORDER BY fonte, tipo_ocorrencia"
)
TESTS = (
    "SELECT split_part(id_no, '.', 3) AS teste, resultado, qtd_falhas FROM ("
    "SELECT *, row_number() OVER (PARTITION BY id_no ORDER BY id_execucao DESC) AS n "
    "FROM metadata.testes_resultados WHERE tipo = 'test') WHERE n = 1 AND resultado IN ('warn', 'fail') "
    "ORDER BY teste"
)


def _table(headers: list[str], body: list[list[Any]]) -> list[str]:
    if not body:
        return ["Nenhuma.", ""]
    out = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    out += ["| " + " | ".join("" if v is None else str(v) for v in r) + " |" for r in body]
    return [*out, ""]


def _day(moment: Any) -> str:
    return f"{moment:%Y-%m-%d}" if moment else ""


def markdown(con: Connection) -> str:
    """O documento. Determinístico: a data é a da última verificação registrada, não a de hoje."""
    until = scalar(con, "SELECT max(dt_verificacao) FROM metadata.fontes_verificacoes")
    lines = [TITLE, "", INTRO, ""]
    lines += [
        f"Dados até a última verificação, em {until:%Y-%m-%d %H:%M} UTC." if until else "Sem verificações.",
        "",
    ]

    lines += ["## Ocorrências em aberto", ""]
    lines += _table(
        ["Fonte", "Dataset", "Partição", "Tipo", "Desde", "Observações", "Verificação (evidência)"],
        [
            [
                r["fonte"],
                r["dataset"],
                r["particao"],
                r["tipo_ocorrencia"],
                _day(r["dt_primeira_observacao"]),
                r["qtd_observacoes"],
                r["id_verificacao"],
            ]
            for r in rows(con, OPEN)
        ],
    )

    lines += ["## Ocorrências por fonte e tipo, em todo o histórico", ""]
    lines += _table(
        ["Fonte", "Tipo", "Ocorrências", "Em aberto"],
        [[r["fonte"], r["tipo_ocorrencia"], r["qtd"], r["abertas"]] for r in rows(con, BY_TYPE)],
    )

    lines += ["## Capturas por dataset", ""]
    lines += _table(
        [
            "Fonte",
            "Dataset",
            "Capturas",
            "Partições",
            "Primeira captura",
            "Última captura",
            "Última verificação",
        ],
        [
            [
                r["fonte"],
                r["dataset"],
                r["qtd_capturas"],
                r["qtd_particoes"],
                _day(r["dt_primeira_captura"]),
                _day(r["dt_ultima_captura"]),
                _day(r["dt_ultima_verificacao"]),
            ]
            for r in rows(con, "SELECT * FROM marts.agg_fontes_capturas ORDER BY fonte, dataset")
        ],
    )

    lines += ["## Lacunas medidas pelos testes de dado", "", LACUNAS, ""]
    lines += _table(
        ["Teste", "Resultado", "Linhas"],
        [[r["teste"], r["resultado"], r["qtd_falhas"]] for r in rows(con, TESTS)],
    )
    return "\n".join(lines)
