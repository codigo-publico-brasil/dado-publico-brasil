# AGENTS.md

Regras para agentes de IA neste repositório. `CLAUDE.md` aponta para cá. Quem revisa e faz o merge é sempre uma pessoa.

## Princípio

**Quanto menos código e menos estrutura, melhor.** Prefira declaração (YAML, SQL do dbt) e o que dlt, dbt e DuckDB já fazem a código próprio. Seja sucinto, mas resolva o problema da melhor forma: estrutura simples reduz a manutenção e os tokens gastos por agentes.

## Antes de começar

Leia `README.md`, `docs/README.md` (mapa da documentação) e `docs/01-entender/03-camadas.md`. Não contrarie um ADR de `docs/05-decisoes/` sem propor outro. **Proponha antes de executar** qualquer mudança de arquitetura, estrutura ou ferramenta e espere aprovação. Se faltar contexto, pergunte.

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
5. **Documentação no mesmo PR:** quem muda comportamento, camada, comando, tabela ou estrutura de pastas atualiza o documento correspondente (e o `README.md` se a estrutura mudar). Doc desatualizada é bug.
6. Erro recorrente de agente vira regra aqui ou teste.

## Onde mexer

| Para... | Edite |
| --- | --- |
| fonte (URL, colunas, chaves, credenciais por `${VARIAVEL}`) | `sources/<poder>/<esfera>/<fonte>.yml` |
| jeito de obter ou ler que o padrão não cobre (SOAP, robô, zip) | `src/dado_publico_brasil/ingestion/custom/<poder>/<esfera>/<fonte>.py` |
| regra de transformação, teste de dado, descrição de coluna | `dbt/` (modelos, YAML ao lado) |
| tabela própria (metadata, identity) | `ddl/` |
| ordem das etapas, agendamento | `src/dado_publico_brasil/orchestration/` |
| ambiente (pasta de dados, warehouse) | variáveis `DADO_PUBLICO_STORAGE_ROOT`, `DADO_PUBLICO_WAREHOUSE` |

`src/dado_publico_brasil/`: `ingestion` e `transformation` só importam `core`; só `orchestration` conhece os dois (um teste confere). Termos técnicos em inglês (landing, raw, staging, intermediate, marts); entidades em português (`pessoas`, `proposicoes`, `votos`). Comando: `uv run dado-publico` (`run`, `extract`, `load`, `transform`, `identity`, `publish`, `catalog`, `docs`, `query`, `verify`, `coverage`, `observe`; `--foreach N` roda os datasets por item e `--dataset` escolhe um).

O fundador usa o projeto para aprender arquitetura de dados e de sistemas: explique decisões e alternativas em poucas linhas e aponte o que merece ADR.

## Nomes e descrições

Leia [`docs/03-consultar/02-convencao-de-nomes.md`](docs/03-consultar/02-convencao-de-nomes.md) antes de criar ou alterar tabela ou coluna: tabelas com o tema na frente e sem conectivos (`proposicoes_autorias`); colunas com prefixo de tipo, `id_`, `dt_` e `fl_`, sem duplicar o tipo (`dt_nascimento`); toda tabela e coluna descrita, em todas as camadas. Padronizar nunca apaga a origem: o dado precisa ser auditável pelo público.

## Documentação

Mapa em [`docs/README.md`](docs/README.md): `01-entender` (explica), `02-fazer` (passo a passo), `03-consultar` (referência), `04-dominio` (instituições), `05-decisoes` (ADRs), `99-historico` (não editar). Arquivos levam `NN-` pela ordem de leitura.

- **Um assunto, um lugar:** antes de escrever, procure se já existe; os outros arquivos linkam, não copiam.
- Todo documento começa dizendo para quem é e o que responde. Explique o porquê e as alternativas, não só o como.
- O catálogo (`03-consultar/01-catalogo.md`) é gerado; nunca edite à mão.
- Decisão aceita não se edita: novo ADR, e a situação do antigo muda no índice de `05-decisoes/README.md`.
- Pendência e decisão aberta são issues, nunca `.md`.

## Lições de experiência

- **Confira antes de afirmar:** leia o arquivo, rode o comando ou busque no código antes de dizer que algo existe, falta ou está desatualizado.
- Ao mover arquivos, use `git mv` e reescreva os links (inclusive em código e testes); depois confira que nenhum link relativo ficou quebrado.
- O `uv` pode não estar no PATH do shell do agente (no Windows fica em `~/.local/bin`).
- Os testes que montam o pipeline sintético levam minutos; rode os arquivos afetados antes da suíte completa.
- Branch empilhada sobre outra ainda não mergeada: diga isso no PR.
