"""O `transform` migra o warehouse antes do dbt: o dbt lê `metadata.capturas`, que só existe migrado."""

from pathlib import Path
from typing import Any

import pytest

from dado_publico_brasil.core import migrations
from dado_publico_brasil.core.settings import Settings
from dado_publico_brasil.transformation import build, dbt


class Stop(Exception):
    pass


def test_transform_applies_migrations_before_dbt(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    calls: list[str] = []

    class Closeable:
        def close(self) -> None:
            calls.append("fechou")

    def opened(settings: Settings) -> Closeable:
        calls.append("migrou")
        return Closeable()

    def invoke(*args: Any, **kwargs: Any) -> None:
        calls.append("dbt")
        raise Stop

    monkeypatch.setattr(migrations, "open_warehouse", opened)
    monkeypatch.setattr(dbt, "invoke", invoke)
    with pytest.raises(Stop):
        build.transform(Settings(storage_root=tmp_path), "transform_pre")
    assert calls == ["migrou", "fechou", "dbt"]
