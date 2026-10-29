# Dado Público Brasil

Os dados abertos do poder público brasileiro, capturados da fonte oficial, organizados em tabelas prontas para consulta e **auditáveis**: cada dado carrega a fonte, a URL e a data de captura.

Este repositório é a camada de dados do projeto [Código Público Brasil](https://github.com/codigo-publico-brasil). É genérica: qualquer aplicação pode consumir os dados, e ela não depende de nenhuma. Serve também de material de estudo de engenharia de dados: a documentação explica cada decisão e as alternativas.

## Por que existe

Os dados públicos estão espalhados em portais com formatos diferentes, mudam sem aviso e raramente dizem de onde vieram. Aqui eles são capturados sem alteração, tratados em etapas que se refazem a partir do original e entregues com o rastro até a página oficial.

## Regras de dados (nunca violar)

1. Todo dado carrega fonte oficial, URL e data de captura.
2. O landing (arquivo recebido) é imutável, com hash.
3. Nada é inventado, estimado ou completado: faltou, fica vazio, e a lacuna é medida por teste.
4. Nenhum documento pessoal (CPF, RG...); só dado público de agente público.
5. Sem métricas avaliativas derivadas (nota, ranking): a plataforma entrega fatos.
6. Conteúdo gerado por IA fica em tabelas próprias, rotulado com modelo e versão, nunca misturado ao dado oficial.

## O que você encontra

| Fonte oficial | O que entra | Tabelas principais |
| --- | --- | --- |
| Câmara dos Deputados | deputados, proposições, autorias, tramitações, votações e voto de cada deputado, órgãos, frentes | `dim_pessoas`, `fct_proposicoes`, `fct_votacoes`, `fct_votos` |
| Senado Federal | senadores, votações e votos, normas, vetos | `fct_normas`, `fct_vetos`, `fct_vetos_votos` |
| TSE | candidaturas, mandatos, bens, votos e contas de campanha | `fct_candidaturas`, `fct_mandatos`, `fct_candidaturas_bens` |
| Portal da Transparência | emendas parlamentares, convênios e favorecidos | `fct_emendas`, `fct_emendas_convenios` |
| Constituição de 1988 | texto por dispositivo | `dim_constituicao_dispositivos` |
| Diário Oficial da União | arquivos originais, só guardados | (sem tabela) |

Pessoas são ligadas entre as fontes por uma chave própria (`id_pessoa`), com regras conservadoras ([identidade de pessoas](docs/01-entender/05-identidade-de-pessoas.md)). Todas as tabelas e colunas estão no [catálogo](docs/03-consultar/01-catalogo.md); o que cada fonte não entrega, em [cobertura e lacunas](docs/03-consultar/04-cobertura-e-lacunas.md).

## Como funciona

```text
fonte oficial ─► landing ─► raw ─► staging ─► intermediate ─► marts ─► PostgreSQL ─► aplicações
                (arquivos   (dlt)   └──────── dbt ────────┘     (publish)  (só leitura)
                 + hash)
```

O arquivo original nunca é alterado; o resto se refaz a partir dele. Cada camada, o porquê das ferramentas (dlt, dbt, DuckDB, Dagster, PostgreSQL) e as alternativas descartadas estão em [arquitetura](docs/01-entender/02-arquitetura.md) e [camadas](docs/01-entender/03-camadas.md).

## Estado

Projeto em desenvolvimento, **ainda sem versão publicada e sem garantia de estabilidade** dos nomes de tabelas e colunas.

- **Funciona hoje:** captura com hash e monitoramento das fontes; carga e transformação em camadas com testes de qualidade; identidade de pessoas; catálogo e dicionário de colunas; cópia dos marts para um PostgreSQL local de leitura.
- **Falta:** infraestrutura de produção, trilha de documentos com busca vetorial, estados e municípios, e a publicação aberta dos dados.
- **Pendências e decisões abertas:** [issues do repositório](https://github.com/codigo-publico-brasil/dado-publico-brasil/issues).

## Começar em poucos minutos

Requisitos: Python 3.13 e [uv](https://docs.astral.sh/uv/).

```bash
uv sync --all-extras                          # instala o ambiente
uv run dado-publico run --years 2025 2026     # captura, carrega e transforma (os dados ficam em data_store/)
uv run dado-publico query --sql "SELECT * FROM marts.pessoas LIMIT 10"
```

**Todas as opções do `dado-publico`** (comandos, modos de execução, filtros por fonte, dataset e ano) estão em `uv run dado-publico --help`, que é a referência completa e sempre atual.

Conexões e segredos vão no `.env` (modelo em `.env.example`, fora do git). PostgreSQL, [Dagster](docs/02-fazer/01-rodar-localmente.md#dagster-interface-agendamento-e-linhagem), auditoria e os outros modos de execução: [rodar localmente](docs/02-fazer/01-rodar-localmente.md).

## Estrutura das pastas

| Pasta | O que é |
| --- | --- |
| `sources/` | declaração das fontes: `sources/<poder>/<esfera>/<fonte>.yml` |
| `src/dado_publico_brasil/` | o código: `core` (base), `ingestion`, `transformation` e `orchestration` (liga os dois) |
| `dbt/` | modelos SQL: staging, intermediate e marts (`dim_`, `fct_`, `brg_`, `agg_`, `app_`), com testes |
| `ddl/` | migrações das tabelas próprias (`metadata`, `identity`) |
| `docs/` | a documentação |
| `tests/` | testes |
| `docker/`, `compose.yaml` | PostgreSQL de desenvolvimento |
| `data_store/` | landing e warehouse (fora do git) |

## Documentação

Ordem de leitura e regras em [`docs/README.md`](docs/README.md).

| Quero... | Leia |
| --- | --- |
| entender o que é e por quê | [`docs/01-entender/`](docs/01-entender/): visão geral, arquitetura, camadas, ferramentas |
| rodar, operar, auditar ou acrescentar uma fonte | [`docs/02-fazer/`](docs/02-fazer/), com o [tutorial de nova fonte](docs/02-fazer/02-tutorial-nova-fonte.md) |
| saber quais tabelas e colunas existem, os nomes e as lacunas | [`docs/03-consultar/`](docs/03-consultar/) |
| entender a Câmara, o Senado, o TSE | [`docs/04-dominio/`](docs/04-dominio/) |
| ver por que cada decisão foi tomada | [`docs/05-decisoes/`](docs/05-decisoes/) |
| trabalhar com IA neste repositório | [`AGENTS.md`](AGENTS.md) |

## Contribuir e pedir ajuda

- **Dúvida, erro ou sugestão:** abra uma [issue](https://github.com/codigo-publico-brasil/dado-publico-brasil/issues). Para corrigir um dado, inclua o link da fonte oficial.
- **Código e documentação:** veja [`CONTRIBUTING.md`](CONTRIBUTING.md). Quem revisa e faz o merge é sempre uma pessoa.
- **Vulnerabilidade ou dado pessoal exposto:** veja [`SECURITY.md`](SECURITY.md).

## Licença

Pretende-se AGPL-3.0 para o código e CC BY 4.0 para os dados curados, **ainda não confirmadas**: por isso o repositório não traz um arquivo `LICENSE` e nenhuma permissão de uso está concedida até a decisão. Os dados de origem seguem os termos de cada fonte oficial.
