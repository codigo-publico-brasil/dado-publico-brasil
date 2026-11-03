"""Site estático do dbt: só o projeto, sem pacotes nem exposures."""

import json

import pytest

from dado_publico_brasil.transformation import branding, dbt, observability


def test_the_static_site_keeps_only_the_project() -> None:
    manifest = {
        "nodes": {"model.p.a": {"package_name": "p"}, "model.elementary.b": {"package_name": "elementary"}},
        "macros": {"macro.p.m": {"package_name": "p"}, "macro.dbt_utils.n": {"package_name": "dbt_utils"}},
        "exposures": {"exposure.p.app": {}},
        "parent_map": {"model.p.a": [], "model.elementary.b": [], "exposure.p.app": ["model.p.a"]},
        "child_map": {"model.p.a": ["exposure.p.app", "model.elementary.b"], "model.elementary.b": []},
    }
    catalog: dict[str, dict[str, dict[str, str]]] = {"nodes": {"model.p.a": {}, "model.elementary.b": {}}}
    html = f"<script>x={{manifest:{json.dumps(manifest)},catalog:{json.dumps(catalog)}}};y=1</script>"
    out = dbt.prune_static(html, project="p")
    start = out.index("{manifest:") + len("{manifest:")
    kept, end = json.JSONDecoder().raw_decode(out, start)
    assert list(kept["nodes"]) == ["model.p.a"] and list(kept["macros"]) == ["macro.p.m"]
    assert kept["exposures"] == {} and kept["child_map"] == {"model.p.a": []}
    assert list(kept["parent_map"]) == ["model.p.a"]
    assert '"model.elementary.b"' not in out[out.index(",catalog:") :] and out.endswith(";y=1</script>")


def test_branding_sets_title_icon_and_a_link_back_home_or_fails_loudly() -> None:
    page = '<html><head><title>dbt Docs</title><link rel="shortcut icon" href="x.ico"/></head><body></body></html>'
    out = branding.apply(page, "Dado Público Brasil · Tabelas")
    assert "<title>Dado Público Brasil · Tabelas</title>" in out and "x.ico" not in out
    assert 'id="cpb-voltar" href="/"' in out and out.count("</body>") == 1
    with pytest.raises(ValueError):
        branding.apply("<html><body></body></html>", "x")


def test_the_report_menu_drops_cloud_pages_and_empty_groups_and_blocks_third_parties() -> None:
    item = "icon:A.jsx(a,{})"
    cloud = f'{{key:"c",path:"https://x",label:"Catalog",description:"d",{item},isSaasPage:!0,tooltip:"t"}}'
    own = f'{{key:"d",path:"/report/dashboard",label:"Dashboard",description:"d",{item}}}'
    menu = f"<head>x</head>const m={{OVERVIEW:[{own},{cloud}],SETUP:[{cloud}]}};"
    out = observability.prune_report(menu)
    assert "isSaasPage" not in out and "SETUP" not in out and "Dashboard" in out
    assert "connect-src 'self'" in out
    with pytest.raises(ValueError):
        observability.prune_report("<head></head>sem menu")
