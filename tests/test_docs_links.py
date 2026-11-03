"""Links relativos da documentação (.md e .html) apontam para arquivos que existem."""

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FILES = [p for p in [*ROOT.glob("*.md"), *(ROOT / "docs").rglob("*.md"), *(ROOT / "docs").rglob("*.html")]]
LINK = re.compile(r'(?:\]\(|href=")([^)"\s]+)')


@pytest.mark.parametrize("doc", FILES, ids=lambda p: str(p.relative_to(ROOT)))
def test_links_relativos_existem(doc: Path) -> None:
    text = doc.read_text(encoding="utf-8")
    text = re.sub(r"```.*?```", "", text, flags=re.S)
    quebrados = []
    for target in LINK.findall(text):
        if re.match(r"([a-z]+:|#|mailto:)", target):
            continue
        path = target.split("#", 1)[0]
        if path and not (doc.parent / path).exists():
            quebrados.append(target)
    assert not quebrados, quebrados
