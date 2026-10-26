# Plataforma de dados

Camada de dados oficial do projeto [Código Público Brasil](https://github.com/codigo-publico-brasil): captura dados abertos do poder público, organiza em camadas e os entrega prontos, com fonte, URL e data de captura, para qualquer aplicação consumir. Código aberto (AGPL-3.0) e dados curados abertos (CC BY 4.0), a confirmar. A documentação também é material de estudo: explica cada decisão.

## Regras de dados (nunca violar)

1. Todo dado carrega fonte oficial, URL e data de captura.
2. O landing (arquivo recebido) é imutável, com hash.
3. Nada é inventado, estimado ou completado: faltou, fica vazio, e a lacuna é medida por teste.
4. Nenhum documento pessoal (CPF, RG...); só dado público de agente público.
5. Sem métricas avaliativas derivadas (nota, ranking): a plataforma entrega fatos.
6. Conteúdo gerado por IA fica em tabelas próprias, rotulado com modelo e versão, nunca misturado ao dado oficial.

## Estado

| Parte | Situação |
| --- | --- |
| Ingestão (Câmara, Senado, TSE, Transparência, Constituição, DOU) | Funcionando: captura com hash, carga no raw, monitoramento e datasets por item em lotes auditáveis |
| Transformação | Funcionando: dbt em camadas, identidade de pessoas, testes, catálogo |
| Orquestração | Linha de comando e Dagster |
| PostgreSQL de serviço | Funcionando em desenvolvimento local (`dado-publico publish`) |
| Documentos e vetores, infraestrutura de produção | A fazer |

## Começar

Requisitos: Python 3.13 e [uv](https://docs.astral.sh/uv/).

```bash
uv sync --all-extras                          # instala o ambiente
uv run dado-publico run --years 2025 2026     # captura, carrega e transforma
uv run dado-publico query --sql "SELECT * FROM marts.pessoas LIMIT 10"
```

Antes de um PR: `uv run ruff check . && uv run ruff format --check . && uv run mypy && uv run pytest` (o que cada um confere está em [`04-ferramentas.md`](docs/01-entender/04-ferramentas.md)). Os dados ficam em `data_store/`, fora do git; conexões e segredos vão no `.env` (modelo em `.env.example`).

## Pastas

| Pasta | O que é |
| --- | --- |
| `sources/` | declaração das fontes: `sources/<poder>/<esfera>/<fonte>.yml` |
| `src/dado_publico_brasil/` | o código: `core` (base), `ingestion`, `transformation` e `orchestration` (liga os dois) |
| `dbt/` | modelos SQL: staging, intermediate, marts, com testes |
| `ddl/` | migrações das tabelas próprias (`metadata`, `identity`) |
| `docs/` | a documentação (mapa abaixo) |
| `tests/` | testes |
| `docker/`, `compose.yaml` | PostgreSQL de desenvolvimento |
| `data_store/` | landing e warehouse (fora do git) |

O fluxo: fonte oficial → `landing` (arquivos com hash) → `raw` (dlt) → `staging` → `intermediate` → `marts` (dbt). Explicado em [`03-camadas.md`](docs/01-entender/03-camadas.md).

## Documentação

Ordem de leitura e regras em [`docs/README.md`](docs/README.md).

| Quero... | Leia |
| --- | --- |
| entender o que é e por quê | [`docs/01-entender/`](docs/01-entender/): visão geral, arquitetura, camadas, ferramentas |
| rodar, operar, auditar ou acrescentar uma fonte | [`docs/02-fazer/`](docs/02-fazer/) |
| saber quais tabelas e colunas existem, os nomes e as lacunas | [`docs/03-consultar/`](docs/03-consultar/) |
| entender a Câmara, o Senado, o TSE | [`docs/04-dominio/`](docs/04-dominio/) |
| ver por que cada decisão foi tomada | [`docs/05-decisoes/`](docs/05-decisoes/) |
| trabalhar com IA neste repositório | [`AGENTS.md`](AGENTS.md) |

## Como contribuir

Ainda não recebemos contribuições de código. Para sugerir correção de dado, abra uma issue com o link da fonte oficial. Pendências e decisões abertas ficam nas issues deste repositório.
