"""O raw só fica "Unsynced" (StaleStatus.STALE) quando o conteúdo do landing mudou, não a cada captura."""

from collections.abc import Iterator

from dagster import (
    AssetKey,
    AssetsDefinition,
    AssetSpec,
    DagsterInstance,
    DataVersion,
    MaterializeResult,
    asset,
    materialize,
    multi_asset,
)
from dagster._core.definitions.data_version import StaleStatus
from dagster._core.loader import LoadingContextForTest

LANDING, RAW = AssetKey(["landing", "x"]), AssetKey(["x", "t"])


def _assets(
    content: list[str],
) -> list[AssetsDefinition]:  # mesma estrutura de `_source_assets` em definitions.py
    @asset(key=LANDING)
    def landing() -> MaterializeResult[None]:
        return MaterializeResult(data_version=DataVersion(content[0]))

    @multi_asset(specs=[AssetSpec(RAW, deps=[LANDING], skippable=True)], name="raw_x")
    def raw() -> Iterator[MaterializeResult[None]]:
        yield MaterializeResult(asset_key=RAW)

    return [landing, raw]


# API de status do Dagster 1.13 (interna; o selo "Unsynced" da interface é StaleStatus.STALE)
def _status(instance: DagsterInstance, assets: list[AssetsDefinition]) -> StaleStatus:
    from dagster._core.definitions.assets.graph.asset_graph import AssetGraph
    from dagster._core.definitions.data_version import CachingStaleStatusResolver

    resolver = CachingStaleStatusResolver(
        instance, AssetGraph.from_assets(assets), LoadingContextForTest(instance)
    )
    return resolver.get_status(RAW)


def test_same_content_keeps_raw_synced_and_new_content_makes_it_stale() -> None:
    content = ["a"]
    assets = _assets(content)
    with DagsterInstance.ephemeral() as inst:
        materialize(assets, instance=inst)
        assert _status(inst, assets) == StaleStatus.FRESH
        materialize([assets[0]], instance=inst)  # a captura da noite, sem dado novo
        assert _status(inst, assets) == StaleStatus.FRESH
        content[0] = "b"
        materialize([assets[0]], instance=inst)
        assert _status(inst, assets) == StaleStatus.STALE
