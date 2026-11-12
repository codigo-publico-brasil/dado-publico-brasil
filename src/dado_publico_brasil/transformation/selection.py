"""Quais modelos do dbt construir em cada fase (ADR 0047): os com entrada nova, e tudo na dúvida.

Lê o `manifest.json` do dbt e o histórico em `metadata` (capturas, execuções e resultado de cada nó); não
conhece fonte nem tabela. Um modelo entra se, desde a última construção dele:

- o raw que ele lê recebeu carga (`metadata.capturas.dt_carga`, por fonte e dataset);
- a identidade mudou (impressão diferente antes e depois da etapa `identity`) e ele lê `identity.*`;
- o período de que depende mudou (tag `data_atual`, `meta.periodo: ano | mes | dia`);
- um modelo de que ele depende foi construído depois dele (inclusive na outra fase);
- ele ou um teste dele não terminou com sucesso, ou nunca rodou.

E todo descendente de quem entrou. Tudo se refaz (sem seleção) sem estado, com outro commit ou código não
commitado, e no primeiro domingo desde a última reconstrução completa: é a rede de segurança.
"""

import json
import re
from dataclasses import dataclass
from datetime import UTC, date, datetime
from graphlib import TopologicalSorter
from pathlib import Path
from typing import Any

from dado_publico_brasil.core import runs
from dado_publico_brasil.core.settings import Settings
from dado_publico_brasil.core.warehouse import Connection
from dado_publico_brasil.transformation import dbt

PRE_TAG = "pre_identity"
PERIOD_TAG = "data_atual"
SUCCESS = ("success", "pass", "warn")  # `warn` é teste com severidade de aviso: não reprova
FAILED = ("fail", "error", "runtime error")
SUNDAY = 6
# `cautious`: um teste só roda quando todos os modelos de que depende já existem (primeira construção);
# `eager`: o teste roda se QUALQUER pai entrou (a entrada alterada de um pai pulado também é testada).
FULL_ARGS = {
    "transform_pre": ("--select", f"tag:{PRE_TAG}", "--indirect-selection", "cautious"),
    "transform_post": ("--exclude", f"tag:{PRE_TAG}", "--indirect-selection", "cautious"),
}


@dataclass(frozen=True)
class Plan:
    stage: str  # transform_pre | transform_post
    full: bool  # reconstrução completa da fase (sem seleção)
    reason: str
    models: frozenset[str]  # unique_id de todos os modelos e seeds da fase
    selected: frozenset[str] = frozenset()  # os que entram (só se não for completa)
    names: tuple[str, ...] = ()
    skipped: tuple[tuple[str, str], ...] = ()  # (esquema, nome) dos pulados
    manifest: Path | None = None  # onde reler os modelos da fase se ainda não havia manifesto ao decidir

    @property
    def skip(self) -> bool:
        return not self.full and not self.names

    @property
    def args(self) -> tuple[str, ...]:
        """Argumentos do `dbt build`. Seletivo = a fase menos os pulados (`--exclude`, uma lista só, que o
        dbt e o Dagster entendem); os testes de quem entrou rodam com `eager` (qualquer pai que entrou)."""
        if self.full:
            return FULL_ARGS[self.stage]
        exclude = [name for _, name in self.skipped]
        phase: tuple[str, ...] = ("--select", f"tag:{PRE_TAG}")
        if self.stage == "transform_post":
            phase, exclude = (), [f"tag:{PRE_TAG}", *exclude]
        return (
            *phase,
            *(("--exclude", " ".join(exclude)) if exclude else ()),
            "--indirect-selection",
            "eager",
        )

    def completed(self, results: list[dict[str, Any]]) -> bool:
        """Foi uma reconstrução completa que deixou resultado de todos os modelos da fase?"""
        models = self.models
        if (
            not models and self.manifest and self.manifest.exists()
        ):  # primeira construção: o dbt o criou agora
            models = _phase_models(json.loads(self.manifest.read_text(encoding="utf-8")), self.stage)
        return self.full and bool(models) and models <= {r["unique_id"] for r in results}


def _minutes(seconds: float) -> str:
    return f"{seconds / 60:.1f}".replace(".", ",") + " min"


def phase_log(plan: Plan, results: list[dict[str, Any]]) -> list[str]:
    """Linhas de log da fase: um resumo e uma linha por modelo (pulado, reconstruído com o tempo, ou erro).

    O Dagster mostra a fase como um passo só; isto deixa no log o que cada modelo fez."""
    built = {
        r["unique_id"].split(".")[-1]: r for r in results if r["unique_id"].startswith(("model.", "seed."))
    }
    errors = [n for n, r in built.items() if r["status"] not in SUCCESS]
    total = sum(r["seconds"] or 0 for r in built.values())
    lines = [
        f"dbt {plan.stage}: {len(plan.skipped)} pulados, {len(built)} reconstruídos "
        f"({_minutes(total)} somados), {len(errors)} com erro"
    ]
    lines += [f"  {name}: pulado" for _, name in plan.skipped]
    for name, r in sorted(built.items(), key=lambda kv: -(kv[1]["seconds"] or 0)):
        lines.append(f"  {name}: {r['status']} ({_minutes(r['seconds'] or 0)})")
    return lines


def _project_nodes(manifest: dict[str, Any]) -> dict[str, Any]:
    project = manifest.get("metadata", {}).get("project_name")
    return {
        i: n
        for i, n in manifest.get("nodes", {}).items()
        if n["resource_type"] in ("model", "seed") and n.get("package_name") == project
    }


def _phase_models(manifest: dict[str, Any], stage: str) -> frozenset[str]:
    """unique_id dos modelos e seeds da fase."""
    return frozenset(
        i
        for i, n in _project_nodes(manifest).items()
        if (PRE_TAG in n.get("tags", [])) == (stage == "transform_pre")
    )


def _dataset(name: str) -> str:
    return re.sub(r"[^0-9a-z]+", "_", name.lower()).strip("_")


def _period(moment: date | datetime, unit: str) -> str:
    return f"{moment:%Y}" if unit == "ano" else f"{moment:%Y-%m-%d}" if unit == "dia" else f"{moment:%Y-%m}"


def _full_reason(con: Connection, stage: str, has_manifest: bool, today: date) -> str | None:
    """Por que reconstruir tudo, ou None se a seleção vale."""
    if not has_manifest:
        return "sem manifesto do dbt"
    last = con.execute(
        "SELECT versao_commit, dt_inicio FROM metadata.execucoes WHERE etapa = ? AND fl_completa "
        "ORDER BY id_execucao DESC LIMIT 1",
        (stage,),
    ).fetchone()
    if last is None:
        return "sem reconstrução completa anterior"
    commit = runs.code_version()
    if commit != last[0] or commit.endswith("+dirty") or commit == "unknown":
        return f"código diferente da última reconstrução completa ({last[0]} -> {commit})"
    if today.weekday() == SUNDAY and last[1].date() < today:
        return "reconstrução completa semanal (domingo)"
    return None


def plan(
    con: Connection, settings: Settings, stage: str, today: date | None = None, force: bool = False
) -> Plan:
    """Decide o que `dbt build` constrói na fase (`transform_pre` ou `transform_post`)."""
    today = today or datetime.now(UTC).date()
    file = dbt.target_dir(settings) / "manifest.json"
    manifest = json.loads(file.read_text(encoding="utf-8")) if file.exists() else {}
    nodes = _project_nodes(manifest)
    models = _phase_models(manifest, stage)
    in_phase = set(models)
    if reason := ("reconstrução completa pedida" if force else _full_reason(con, stage, bool(nodes), today)):
        return Plan(stage, True, reason, models, manifest=file)

    # estado: o último resultado de cada nó e quando começou a execução que o produziu
    latest = {
        r[0]: (r[1], r[2])
        for r in con.execute(
            "SELECT t.id_no, arg_max(t.resultado, t.id_execucao), arg_max(e.dt_inicio, t.id_execucao) "
            "FROM metadata.testes_resultados t JOIN metadata.execucoes e USING (id_execucao) "
            "WHERE t.tipo <> 'freshness' GROUP BY t.id_no"
        ).fetchall()
    }
    loads = {
        (f, _dataset(d)): when
        for f, d, when in con.execute(
            "SELECT fonte, dataset, try_cast(max(dt_carga) AS TIMESTAMP) FROM metadata.capturas "
            "WHERE dt_carga IS NOT NULL GROUP BY 1, 2"
        ).fetchall()
    }
    # identidade mudou na etapa (antes != depois) ou entre duas etapas (antes != depois da anterior)
    changed_at = con.execute(
        "SELECT max(dt_fim) FROM (SELECT dt_fim, impressao_antes AS antes, impressao_depois AS depois, "
        "lag(impressao_depois) OVER (ORDER BY id_execucao) AS anterior FROM metadata.execucoes "
        "WHERE etapa = 'identity') WHERE dt_fim IS NOT NULL AND (antes IS DISTINCT FROM depois "
        "OR (anterior IS NOT NULL AND antes IS DISTINCT FROM anterior))"
    ).fetchone()
    identity_at = changed_at[0] if changed_at else None

    def loaded(source: dict[str, Any]) -> datetime | None:
        """Última carga do dataset da tabela do raw (a filha do dlt é `dataset__filho`)."""
        parts = source["name"].split("__")
        for i in range(len(parts), 0, -1):
            if (when := loads.get((source["source_name"], "__".join(parts[:i])))) is not None:
                return when  # type: ignore[no-any-return]
        return None

    def stale(node: dict[str, Any], built: datetime) -> bool:
        for dep in node.get("depends_on", {}).get("nodes", []):
            if dep in nodes:
                if (parent := latest.get(dep)) and parent[1] > built:
                    return True  # o pai foi refeito depois (por exemplo, na outra fase)
            elif source := manifest["sources"].get(dep):
                if source["source_name"] == "identity":
                    if identity_at is not None and identity_at > built:
                        return True
                elif source["schema"].startswith("raw_") and (when := loaded(source)) and when > built:
                    return True
        unit = (
            str(node.get("config", {}).get("meta", {}).get("periodo", ""))
            if PERIOD_TAG in node["tags"]
            else ""
        )
        return bool(unit) and _period(built, unit) != _period(today, unit)

    dirty: set[str] = set()
    for i, node in nodes.items():
        state = latest.get(i)
        if state is None or state[0] not in SUCCESS or stale(node, state[1]):
            dirty.add(i)
    for i, node in manifest["nodes"].items():  # teste reprovado: o modelo testado é refeito
        if node["resource_type"] == "test" and i in latest and latest[i][0] in FAILED:
            attached = node.get("attached_node")
            dirty |= {
                d
                for d in ([attached] if attached else node.get("depends_on", {}).get("nodes", []))
                if d in nodes
            }

    children: dict[str, set[str]] = {i: set() for i in nodes}
    for i, node in nodes.items():
        for dep in node.get("depends_on", {}).get("nodes", []):
            if dep in nodes:
                children[dep].add(i)
    todo, entering = list(dirty), set(dirty)
    while todo:
        for child in children[todo.pop()] - entering:
            entering.add(child)
            todo.append(child)

    chosen = entering & in_phase
    skipped = sorted(in_phase - chosen)  # ordem topológica: o Dagster exige o pai antes do filho
    return Plan(
        stage,
        False,
        f"{len(chosen)} de {len(in_phase)} modelos",
        models,
        frozenset(chosen),
        tuple(sorted(nodes[i]["name"] for i in chosen)),
        tuple(
            (nodes[i]["schema"], nodes[i]["name"])
            for i in TopologicalSorter(
                {
                    i: [d for d in nodes[i].get("depends_on", {}).get("nodes", []) if d in skipped]
                    for i in skipped
                }
            ).static_order()
        ),
    )
