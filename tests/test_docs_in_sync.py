"""A documentação acompanha o código: chaves do contrato, comandos, variáveis, caminhos e ADRs.

Cada guarda é uma função pura sobre texto, para o teste negativo provar que ela pode reprovar.
"""

import ast
import re
from pathlib import Path

import pytest

from dado_publico_brasil.ingestion import contract

ROOT = Path(__file__).resolve().parents[1]
ESPECIFICACAO = ROOT / "docs/02-fazer/03-especificacao-de-fonte.md"
AGENTS = ROOT / "AGENTS.md"
LISTA_ETAPAS = ROOT / "docs/02-fazer/01-rodar-localmente.md"
ADRS = ROOT / "docs/05-decisoes"
# `99-historico` e o CHANGELOG são registro; os ADRs aceitos não se editam (descrevem o que existia na data).
MD = [
    p
    for p in [*ROOT.glob("*.md"), *(ROOT / "docs").rglob("*.md")]
    if "99-historico" not in p.parts and "05-decisoes" not in p.parts and p.name != "CHANGELOG.md"
] + [ADRS / "README.md"]


def _ler(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def _sem_cercas(texto: str) -> str:
    return re.sub(r"```.*?```", "", texto, flags=re.S)


# (a) chaves do contrato ---------------------------------------------------------------------------------------------
def chaves_do_contrato() -> set[str]:
    """Todo conjunto `*_KEYS` de contract.py: chave nova entra aqui sozinha."""
    return {k for nome in dir(contract) if nome.endswith("_KEYS") for k in getattr(contract, nome)}


def chaves_sem_doc(doc: str, chaves: set[str]) -> list[str]:
    """Chave documentada = `chave` entre crases ou `chave:` em exemplo YAML."""
    return sorted(k for k in chaves if not re.search(rf"(?<![\w-])(`(?:[\w.]*\.)?{k}`|{k}:)", doc))


def test_toda_chave_do_contrato_esta_na_especificacao() -> None:
    assert chaves_do_contrato() >= {"source", "base_url", "tolerated_rejects", "refresh_after_days"}
    assert not chaves_sem_doc(_ler(ESPECIFICACAO), chaves_do_contrato())


def test_chave_sem_doc_reprova() -> None:
    doc = _ler(ESPECIFICACAO).replace("tolerated_rejects", "xx")
    assert chaves_sem_doc(doc, chaves_do_contrato()) == ["tolerated_rejects"]


# (b) subcomandos do CLI ---------------------------------------------------------------------------------------------
def comandos_do_cli() -> set[str]:
    tree = ast.parse(_ler(ROOT / "src/dado_publico_brasil/orchestration/__main__.py"))
    for n in ast.walk(tree):
        if isinstance(n, ast.Assign) and any(getattr(t, "id", "") == "COMMANDS" for t in n.targets):
            return set(ast.literal_eval(n.value))
    raise AssertionError("COMMANDS não encontrado")


def comandos_com_problema(comandos: set[str], agents: str, etapas: str, docs: dict[str, str]) -> list[str]:
    """Comando que falta na lista do AGENTS.md, e comando citado (nas listas ou em `dado-publico X`) que não existe."""
    problemas = []
    lista_agents = re.search(r"Comando: `uv run dado-publico` \((.*?)\)", agents, re.S)
    lista_etapas = re.search(r"Etapas separadas: (.*?)\n", etapas)
    assert lista_agents and lista_etapas, "a lista de comandos mudou de lugar: ajuste o teste"
    for nome, lista in (
        ("AGENTS.md", lista_agents.group(1)),
        ("01-rodar-localmente.md", lista_etapas.group(1)),
    ):
        citados = {m.split()[0] for m in re.findall(r"`([a-z][^`]*)`", lista)}
        if nome == "AGENTS.md":
            problemas += [f"{nome}: falta `{c}`" for c in sorted(comandos - citados)]
        problemas += [f"{nome}: `{c}` não existe" for c in sorted(citados - comandos)]
    for nome, texto in docs.items():
        for c in re.findall(r"dado-publico(?:\.exe)? ([a-z][a-z-]*)", texto):
            if c not in comandos:
                problemas.append(f"{nome}: `dado-publico {c}` não existe")
    return problemas


def test_comandos_da_doc_batem_com_o_cli() -> None:
    docs = {str(p.relative_to(ROOT)): _ler(p) for p in MD}
    assert not comandos_com_problema(comandos_do_cli(), _ler(AGENTS), _ler(LISTA_ETAPAS), docs)


def test_comando_novo_ou_removido_reprova() -> None:
    cmds, agents, etapas = comandos_do_cli(), _ler(AGENTS), _ler(LISTA_ETAPAS)
    assert comandos_com_problema(cmds | {"novo"}, agents, etapas, {}) == ["AGENTS.md: falta `novo`"]
    assert comandos_com_problema(cmds - {"recheck"}, agents, etapas, {})  # a doc cita um que não existe mais
    assert comandos_com_problema(cmds, agents, etapas, {"x.md": "uv run dado-publico fantasma"})


# (c) variáveis de ambiente ------------------------------------------------------------------------------------------
def variaveis_do_codigo() -> set[str]:
    achadas = set()
    for p in (ROOT / "src").rglob("*.py"):
        achadas |= {v.rstrip("_") for v in re.findall(r"DADO_PUBLICO_[A-Z0-9_]*[A-Z0-9_]", _ler(p))}
    return achadas


def variaveis_sem_doc(variaveis: set[str], texto: str) -> list[str]:
    return sorted(v for v in variaveis if v not in texto)


def _texto_das_variaveis() -> str:
    return "\n".join(_ler(p) for p in [*MD, ROOT / ".env.example", ROOT / ".env.servidor.example"])


def test_toda_variavel_de_ambiente_esta_documentada() -> None:
    assert "DADO_PUBLICO_STORAGE_ROOT" in variaveis_do_codigo()
    assert not variaveis_sem_doc(variaveis_do_codigo(), _texto_das_variaveis())


def test_variavel_sem_doc_reprova() -> None:
    assert variaveis_sem_doc({"DADO_PUBLICO_NAO_EXISTE_NA_DOC"}, _texto_das_variaveis())


# (d) caminhos citados -----------------------------------------------------------------------------------------------
CAMINHO = re.compile(r"`((?:src|dbt|sources|ddl|tests|scripts|docs|\.github)/[^`\s]+)`")
# Exceções (caminho citado -> motivo): só exemplo ou caminho futuro; defasagem se corrige na doc, não aqui.
ALLOWED: dict[str, str] = {}


def caminhos_quebrados(doc: str, raiz: Path) -> list[str]:
    quebrados = []
    for c in CAMINHO.findall(_sem_cercas(doc)):
        c = re.split(r"[#:]", c.rstrip(".,;)"))[0]  # âncora e `:linha` não fazem parte do caminho
        if any(ch in c for ch in "*<>{}$…") or "..." in c or c in ALLOWED:
            continue  # padrão ou modelo com marcador: não é um caminho literal
        if not (raiz / c).exists():
            quebrados.append(c)
    return quebrados


@pytest.mark.parametrize("doc", MD, ids=lambda p: str(p.relative_to(ROOT)))
def test_caminhos_citados_existem(doc: Path) -> None:
    assert not caminhos_quebrados(_ler(doc), ROOT)


def test_caminho_inexistente_reprova(tmp_path: Path) -> None:
    (tmp_path / "src/existe").mkdir(parents=True)
    assert caminhos_quebrados("veja `src/existe/` e `src/nao_existe.py`", tmp_path) == ["src/nao_existe.py"]
    assert not caminhos_quebrados("```\n`src/nao_existe.py`\n```", tmp_path)  # cerca de código é exemplo


# (e) índice de ADRs -------------------------------------------------------------------------------------------------
def _status(arquivo: str) -> str:
    m = re.search(r"^- \*\*Status:\*\* (\w+)", arquivo, re.M)
    assert m, "ADR sem linha Status"
    return m.group(1).lower()


def indice_com_problema(indice: str, adrs: dict[str, str]) -> list[str]:
    """`adrs`: nome do arquivo -> texto. Cada ADR está no índice e a situação do índice não contradiz o arquivo."""
    linhas = {}
    for m in re.finditer(r"^\| \[\d{4}\]\(([^)]+)\) \|.*\| ([^|]+) \|$", indice, re.M):
        linhas[m.group(1)] = m.group(2).strip().lower()
    problemas = [f"{n} fora do índice" for n in sorted(adrs) if n not in linhas]
    for n, texto in adrs.items():
        situacao, status = linhas.get(n, ""), _status(texto)
        if status == "proposto" and not situacao.startswith(("proposto", "substituído")):
            problemas.append(f"{n}: arquivo proposto, índice '{situacao}'")
        if status == "defasado" and not situacao.startswith("defasado"):
            problemas.append(f"{n}: arquivo defasado, índice '{situacao}'")
        if status == "aceito" and situacao.startswith(("proposto", "defasado")):
            problemas.append(f"{n}: arquivo aceito, índice '{situacao}'")
    return problemas


def _adrs() -> dict[str, str]:
    return {p.name: _ler(p) for p in ADRS.glob("[0-9]*.md")}


def test_indice_de_adrs_bate_com_os_arquivos() -> None:
    assert not indice_com_problema(_ler(ADRS / "README.md"), _adrs())


def test_indice_de_adrs_reprova_adr_ausente_ou_status_trocado() -> None:
    indice, adrs = _ler(ADRS / "README.md"), _adrs()
    assert indice_com_problema(indice, {**adrs, "9999-novo.md": "- **Status:** aceito"})
    primeiro = next(n for n, t in adrs.items() if _status(t) == "aceito")
    trocado = adrs[primeiro].replace("**Status:** aceito", "**Status:** proposto", 1)
    assert indice_com_problema(indice, {**adrs, primeiro: trocado})
