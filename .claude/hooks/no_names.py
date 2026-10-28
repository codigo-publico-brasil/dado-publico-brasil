"""Gancho do Claude Code: impede o agente de escrever nome de candidato, de partido ou informação do tipo.

Vale para o que o agente grava em arquivos (comentários de código incluídos) e para commits, PRs e issues
pedidos pelo terminal. A lista e a regra são as de `tests/test_no_names.py` (a mesma do CI); as tabelas de
referência em `dbt/seeds/` ficam de fora. A saída 2 bloqueia a ação e devolve a mensagem ao agente.
"""

import importlib.util
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SKIP = ("dbt/seeds/", "dbt/dbt_packages/", ".venv/", "data_store/")
PUBLISHING = re.compile(r"\bgit\s+commit\b|\bgh\s+(pr|issue)\s+(create|edit|comment)\b")


def forbidden_lines(text: str) -> list[int]:
    spec = importlib.util.spec_from_file_location("no_names_test", ROOT / "tests" / "test_no_names.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return list(module.forbidden_lines(text))


def main() -> int:
    data = json.load(sys.stdin)
    tool, args = data.get("tool_name", ""), data.get("tool_input", {})
    if tool == "Bash":
        command = str(args.get("command", ""))
        texts = [command] if PUBLISHING.search(command) else []
        where = "no commit, PR ou issue"
    else:
        path = Path(str(args.get("file_path", ""))).resolve()
        try:
            relative = path.relative_to(ROOT).as_posix()
        except ValueError:
            return 0  # fora do repositório
        if relative.startswith(SKIP):
            return 0
        texts = [str(args.get("content", "")), str(args.get("new_string", ""))]
        texts += [str(e.get("new_string", "")) for e in args.get("edits", [])]
        where = f"em {relative}"
    lines = [n for t in texts for n in forbidden_lines(t)]
    if lines:
        print(
            f"Bloqueado: nome de candidato ou sigla de partido {where} (linha(s) {sorted(set(lines))}). "
            'Use rótulos genéricos ("Pessoa Exemplo", "Partido A"), inclusive em comentários, docstrings, '
            "mensagens de commit e descrições de PR. Veja a regra no AGENTS.md.",
            file=sys.stderr,
        )
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
