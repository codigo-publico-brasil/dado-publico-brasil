# ADR 0048: medir a cobertura dos testes no CI, sem piso a princípio

- **Status:** proposto (2026-11-10), para revisão do fundador
- **Data:** 2026-11-10

## Contexto

Os testes passam, mas ninguém sabe o que não tem teste, principalmente nas partes que movem dados (issue 41). Medir exige uma dependência de desenvolvimento nova, `pytest-cov` (que traz o `coverage`), e a regra do projeto pede ADR para dependência.

## Decisão

1. Adicionar `pytest-cov` ao grupo `dev`. Não entra no pacote publicado nem na imagem.
2. O CI roda `pytest --cov` e publica o relatório por arquivo (linhas sem teste, cobertura de ramos) no resumo do job. A configuração fica em `[tool.coverage]` do `pyproject.toml`.
3. **Nenhum limite reprova o CI por enquanto.** Depois de algumas medições, os pisos por pacote (`core`, `ingestion`, `transformation`, `orchestration`) são definidos com `fail_under` em novo ADR ou emenda a este, com base no número real.

## Alternativas consideradas

- **Piso global desde já:** o número seria chute e travaria PRs de documentação. Rejeitada.
- **Serviço externo (Codecov etc.):** conta, token e dependência de terceiro por um número que o resumo do job já mostra. Rejeitada.
- **`coverage` puro sem `pytest-cov`:** funciona (`coverage run -m pytest`), mas `pytest-cov` é o padrão e integra os subprocessos e o xdist. Mantida a escolha.

## Consequências

- Um passo a mais de alguns segundos no CI.
- Cobertura alta não prova dado correto: os testes de reconciliação e de lacunas continuam sendo o principal.
