# Plataforma de dados

Camada de dados oficial do projeto [Código Público Brasil](https://github.com/codigo-publico-brasil): captura dados abertos do poder público, organiza em camadas e os entrega prontos, com fonte, URL e data de captura, para qualquer aplicação consumir.

## Propósito

- **Um só lugar para os dados públicos**, de qualquer poder (legislativo, executivo, judiciário) e esfera (federal, estadual, municipal). Hoje: legislativo federal (Câmara dos Deputados e Senado Federal) e, do Judiciário federal, as candidaturas ao Congresso no TSE.
- **Executado em infraestrutura própria de dados:** pipelines agendados, banco de consumo, trilha de documentos com banco vetorial e aplicações de IA, além do ETL clássico. A infraestrutura ainda será escolhida; a plataforma não depende de nenhuma nuvem específica.
- **Código aberto (AGPL-3.0) e dados curados abertos (CC BY 4.0)**, a confirmar.
- **Material de estudo:** a documentação explica cada decisão de arquitetura e de dados.

## Regras de dados (nunca violar)

1. Todo dado carrega fonte oficial, URL e data de captura.
2. O landing (arquivo recebido) é imutável, com hash.
3. Nada é inventado, estimado ou completado: faltou, fica vazio, e a lacuna é medida por teste.
4. Nenhum documento pessoal (CPF, RG...); só dado público de agente público.
5. Sem métricas avaliativas derivadas (nota, ranking): a plataforma entrega fatos.
6. Conteúdo gerado por IA fica em tabelas próprias, rotulado com modelo e versão, nunca misturado ao dado oficial.

As regras de apresentação (neutralidade, sem recomendação de voto) pertencem às aplicações.

## Estado

| Parte | Situação |
| --- | --- |
| Ingestão (Câmara e Senado) | Funcionando: captura com hash (CSV e JSON), carga no raw (dlt), monitoramento de disponibilidade, colunas e volume; datasets por item (tramitação, processos) em lotes auditáveis, por amostra até a carga total ser pedida; código próprio por fonte só quando preciso |
| Transformação | Funcionando: dbt em camadas, identidade de pessoas, testes de qualidade, catálogo e dicionário de colunas |
| Orquestração | Linha de comando e Dagster, com os ativos gerados a partir de `sources/` |
| PostgreSQL de serviço | Funcionando em desenvolvimento local: `dado-publico publish` copia os marts e o papel `leitor` só lê; a identidade tem cópia imutável a cada execução ([ADR 0014](docs/05-decisoes/0014-warehouse-lake-duckdb-e-postgres-de-servico.md)) |
| Documentos e vetores (esqueleto em `documents/`), infraestrutura de produção | A fazer |

Última carga real (2000 a 2026): 190 mil votações, 1,9 milhão de votos, 886 mil proposições, 7,9 mil pessoas.

## Estrutura

```text
src/dado_publico_brasil/   core (base), ingestion, transformation, orchestration; um só pacote com extras
sources/                declaração das fontes: sources/<poder>/<esfera>/<fonte>.yml
dbt/                    projeto dbt: staging, intermediate, marts
ddl/                    migrações SQL das tabelas próprias (metadata, identity)
docs/  tests/             documentação e testes
.env.example            modelo das variáveis de ambiente (o `.env` fica fora do git)
```

O fluxo: fonte oficial → `landing` (arquivos com hash) → `raw_<esfera>_<fonte>` (dlt) → `staging` → `intermediate` → `marts` (dbt). Detalhes em [`docs/01-entender/03-camadas.md`](docs/01-entender/03-camadas.md).

## Como subir o ambiente

Requisitos: Python 3.13 e [uv](https://docs.astral.sh/uv/). Na raiz do repositório:

```bash
uv sync --all-extras
```

```bash
uv run dado-publico run --years 2025 2026
```

Outros modos: `--incremental` (a execução diária: só a partição em curso dos datasets que cada fonte declara como `refresh: daily`) e `--historical --from-year 2000` (carga massiva). Os dados ficam em `data_store/` (fora do git).

**Conexões e segredos** vão em variáveis de ambiente: copie `.env.example` para `.env` (fora do git) e use `uv run --env-file .env dado-publico ...` (o `dagster dev` já carrega o `.env` da pasta). Em produção, a infraestrutura injeta as variáveis, de preferência a partir de um gerenciador de segredos.

```bash
uv run dado-publico query --sql "SELECT * FROM marts.pessoas LIMIT 10"
```

```bash
uv run dado-publico docs
```

O último abre o grafo de linhagem e o dicionário de colunas (dbt docs).

**PostgreSQL de serviço (o que as aplicações leem).** Requer Docker. Defina no `.env` `DADO_PUBLICO_PG_PASSWORD`, `DADO_PUBLICO_PG_LEITOR_PASSWORD` e `DADO_PUBLICO_POSTGRES_DSN` (modelo em `.env.example`) e, a partir desta pasta:

```bash
docker compose up -d
uv run --env-file .env dado-publico publish
```

O `publish` copia todos os marts para o esquema `marts` do PostgreSQL numa troca atômica e dá leitura ao papel `leitor`. Os testes de integração rodam contra o banco `teste` (`DADO_PUBLICO_TEST_POSTGRES`); sem a variável, são pulados. Auditoria e datasets por item:

```bash
uv run dado-publico verify
uv run dado-publico coverage
uv run dado-publico run --incremental --foreach 300
```

`verify` confere os hashes de todo o landing; `coverage` mostra o que já foi buscado nos datasets por item (tramitação, processos); `--foreach N` busca os N itens mais recentes que faltam (a carga total só quando pedida). Para a interface do Dagster (guarde o estado dele em uma pasta absoluta, por exemplo `data_store/.state/dagster`, em `DAGSTER_HOME`):

```bash
uv run dagster dev -m dado_publico_brasil.orchestration.definitions
```

Antes de abrir um PR:

```bash
uv run ruff check . && uv run ruff format --check . && uv run mypy && uv run pytest
```

## Onde ler mais

| Quero... | Leia |
| --- | --- |
| ver as camadas e como executar | [`docs/01-entender/03-camadas.md`](docs/01-entender/03-camadas.md) |
| saber quais tabelas e colunas existem | [`docs/03-consultar/01-catalogo.md`](docs/03-consultar/01-catalogo.md) |
| conferir de onde veio um dado e o que falta | [`docs/02-fazer/05-auditar.md`](docs/02-fazer/05-auditar.md) |
| acrescentar uma fonte | [`docs/02-fazer/03-especificacao-de-fonte.md`](docs/02-fazer/03-especificacao-de-fonte.md) |
| ver o que falta e o que cada fonte não entrega | [`docs/03-consultar/04-cobertura-e-lacunas.md`](docs/03-consultar/04-cobertura-e-lacunas.md) |
| entender a ligação de pessoas entre fontes | [`docs/01-entender/05-identidade-de-pessoas.md`](docs/01-entender/05-identidade-de-pessoas.md) |
| entender a Câmara e como se vota | [`docs/04-dominio/camara-dos-deputados.md`](docs/04-dominio/camara-dos-deputados.md) |
| ver por que cada decisão foi tomada | [`docs/05-decisoes/`](docs/05-decisoes/) |
| trabalhar com IA neste repositório | [`AGENTS.md`](AGENTS.md) |

Índice completo em [`docs/README.md`](docs/README.md). O trabalho é conduzido em itens pequenos no quadro do GitHub Projects.

## Como contribuir

Ainda não recebemos contribuições de código. Para sugerir correção de dado, abra uma issue com o link da fonte oficial.
