"""O grafo do Dagster: nenhum ativo executável depende de ativo-stub, e o job `processar_tudo` segue a ordem."""

import json
import os
import subprocess
import sys
from pathlib import Path

from dado_publico_brasil.core.settings import Settings
from dado_publico_brasil.transformation import dbt

ROOT = Path(__file__).resolve().parents[2]
# Único stub legítimo: `metadata.capturas` é gravada por todas as fontes direto no warehouse, sem ativo próprio.
LEGIT_STUBS = {"metadata/capturas"}

CODE = """
import json
from dagster import AssetKey
from dagster._core.execution.api import create_execution_plan
from dado_publico_brasil.orchestration.definitions import defs

graph = defs.resolve_asset_graph()
stubs = {k for k in graph.get_all_asset_keys() if not graph.get(k).is_executable}
bad = sorted(
    f"{c.to_user_string()} <- {k.to_user_string()}" for k in stubs for c in graph.get(k).child_keys
)
plan = create_execution_plan(defs.resolve_job_def("processar_tudo"))
steps = {s.key: s for s in plan.get_all_steps_in_topo_order()}


def ancestors(key):
    seen, todo = set(), [key]
    while todo:
        for dep in steps[todo.pop()].get_execution_dependency_keys():
            if dep not in seen:
                seen.add(dep)
                todo.append(dep)
    return seen


def step_of(*path):
    return next(k for k, s in steps.items() if AssetKey(list(path)) in [o.properties.asset_key for o in s.step_outputs])


chain = [step_of("intermediate", "int_pessoas_ids_vistos"), step_of("identity", "pessoas"),
         step_of("marts", "dim_pessoas"),
         step_of("publicacao", "lake"), step_of("publicacao", "docs")]
print(json.dumps({"bad": bad, "chain": chain, "linked": [a in ancestors(b) for a, b in zip(chain, chain[1:])]}))
"""


def test_graph_has_no_stub_dependency_and_processing_follows_the_order(tmp_path: Path) -> None:
    settings = Settings(storage_root=tmp_path / "store")
    dbt.invoke(settings, "parse")  # gera o manifesto que o Dagster lê
    env = {**os.environ, "DADO_PUBLICO_STORAGE_ROOT": str(settings.storage_root)}
    result = subprocess.run(
        [sys.executable, "-W", "ignore", "-c", CODE],
        capture_output=True,
        text=True,
        env=env,
        cwd=ROOT,
        check=False,
    )
    assert result.returncode == 0, result.stderr[-1500:]
    out = json.loads(result.stdout.strip().splitlines()[-1])
    stub_links = [b for b in out["bad"] if b.split(" <- ")[1] not in LEGIT_STUBS]
    assert not stub_links, f"ativo executável depende de ativo-stub (sem op): {stub_links}"
    assert len(set(out["chain"])) == 5, out
    assert all(out["linked"]), out  # pre -> identity -> post -> lake -> docs
