# AGENTS.md

Regras para agentes de IA neste repositório. `CLAUDE.md` aponta para cá. Quem revisa e faz o merge é sempre uma pessoa.

## Princípio

**Quanto menos código e menos estrutura, melhor.** Prefira declaração (YAML, SQL do dbt) e o que dlt, dbt e DuckDB já fazem a código próprio. Seja sucinto, mas resolva o problema da melhor forma: estrutura simples reduz a manutenção e os tokens gastos por agentes.

## Antes de começar

Leia `README.md` e `docs/dados/camadas.md`. Não contrarie um ADR de `docs/adr/` sem propor outro. **Proponha antes de executar** qualquer mudança de arquitetura, estrutura ou ferramenta e espere aprovação. Se faltar contexto, pergunte.

## Dados (nunca violar)

- Todo dado exibido tem fonte oficial, URL e data de captura.
- O landing é imutável (arquivo original, hash, URL, data). Nunca edite nem apague.
- Nunca invente, estime nem complete dado: faltou, fica vazio, e o teste mede a lacuna.
- Nenhum documento pessoal (CPF, RG...); nenhum segredo ou dado pessoal no repositório.
- Sem ranking, nota ou métrica avaliativa derivada. Conteúdo de IA fica em tabelas próprias, rotulado.
- Camadas posteriores são reproduzíveis do landing por código; pipelines são idempotentes.
- Se um pedido conflitar com isto, pare e diga qual regra.

## Como trabalhar

1. Testes primeiro, a partir do critério de aceite. Não desative teste para passar.
2. PRs consolidados e coerentes, um assunto por PR. Rode os checks antes:
   ```bash
   uv sync --all-extras
   uv run ruff check . && uv run ruff format --check . && uv run mypy && uv run pytest
   ```
3. Dependência nova só com ADR. Merge e implantação são da pessoa e da esteira.
4. No PR, preencha "autoria da IA": o que a IA escreveu, o que uma pessoa revisou, o que ficou incerto. Commits levam o trailer `Co-Authored-By` do agente.
5. Erro recorrente de agente vira regra aqui ou teste.

## Onde mexer

| Para... | Edite |
| --- | --- |
| fonte (URL, colunas, chaves, credenciais por `${VARIAVEL}`) | `sources/<poder>/<esfera>/<fonte>.yml` |
| jeito de obter ou ler que o padrão não cobre (SOAP, robô, zip) | `src/plataforma_dados/ingestion/custom/<poder>/<esfera>/<fonte>.py` |
| regra de transformação, teste de dado, descrição de coluna | `dbt/` (modelos, YAML ao lado) |
| tabela própria (metadata, identity) | `ddl/` |
| ordem das etapas, agendamento | `src/plataforma_dados/orchestration/` |
| ambiente (pasta de dados, warehouse) | variáveis `PLATAFORMA_STORAGE_ROOT`, `PLATAFORMA_WAREHOUSE` |

`src/plataforma_dados/`: `ingestion` e `transformation` só importam `core`; só `orchestration` conhece os dois (um teste confere). Termos técnicos em inglês (landing, raw, staging, intermediate, marts); entidades em português (`pessoas`, `proposicoes`, `votos`). Comando: `uv run plataforma` (`run`, `extract`, `load`, `transform`, `identity`, `catalog`, `docs`, `query`, `verify`, `coverage`; `--foreach N` roda os datasets por item).

O fundador usa o projeto para aprender arquitetura de dados e de sistemas: explique decisões e alternativas em poucas linhas e aponte o que merece ADR.
