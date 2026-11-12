"""Trava do ADR 0053: o núcleo não nomeia fonte (AGENTS.md, "Princípio").

Os nomes vêm de `sources/<poder>/<esfera>/<fonte>.yml` (nome do arquivo), sem lista própria. O teste lê o AST do
Python de `src/` (fora de `ingestion/custom/`, que é o lugar do que é próprio da fonte) e reprova nome de fonte em
identificador ou texto; comentários `#` não entram. Somam-se a eles os termos de `EXTRA`, que identificam o
calendário da legislatura (ponto A) e a busca em texto de ocorrência (ponto C) e não são nome de fonte.

`EXCECOES` é a dívida de hoje (arquivo e motivo); cada PR do ADR 0053 tira uma parte. Ela só encolhe: arquivo
que deixou de violar tem de sair da lista, e arquivo novo não entra.
"""

import ast
import re
from collections.abc import Iterator
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXTRA = {"legislature", "ainda não publicado"}
EXCECOES = {
    "ingestion/fetch.py": "docstring cita fonte como exemplo (PR 2)",
    "orchestration/__main__.py": "docstring cita fonte como exemplo (PR 2)",
    "transformation/identity.py": "B: fontes de identidade fixas no código (PR 4)",
}


def _termos() -> re.Pattern[str]:
    nomes = {p.stem for p in (ROOT / "sources").glob("*/*/*.yml")} | EXTRA
    return re.compile(rf"(?<![a-z0-9])({'|'.join(map(re.escape, sorted(nomes)))})(?![a-z0-9])")


def _textos(arvore: ast.AST) -> Iterator[str]:
    for n in ast.walk(arvore):
        if isinstance(n, ast.Constant) and isinstance(n.value, str):
            yield n.value
        elif isinstance(n, ast.Name):
            yield n.id
        elif isinstance(n, ast.Attribute):
            yield n.attr
        elif isinstance(n, ast.arg):
            yield n.arg
        elif isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            yield n.name


def _violadores() -> set[str]:
    achado = _termos()
    base = ROOT / "src" / "dado_publico_brasil"
    return {
        rel
        for f in base.rglob("*.py")
        if "custom" not in f.parts
        and (rel := f.relative_to(base).as_posix())
        and any(achado.search(t.lower()) for t in _textos(ast.parse(f.read_text("utf-8"))))
    }


def test_nucleo_nao_nomeia_fonte_fora_das_excecoes() -> None:
    novos = _violadores() - EXCECOES.keys()
    assert not novos, f"nome de fonte no núcleo (mova para o YAML da fonte ou para custom/): {sorted(novos)}"


def test_excecoes_so_encolhem() -> None:
    obsoletas = EXCECOES.keys() - _violadores()
    assert not obsoletas, f"exceção que deixou de ser necessária: tire da lista {sorted(obsoletas)}"
