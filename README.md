# Plataforma de dados

Camada de dados oficial do projeto [Código Público Brasil](https://github.com/codigo-publico-brasil): captura dados abertos do poder público, organiza em camadas e os entrega prontos, com fonte, URL e data de captura, para qualquer aplicação consumir. O [Quem Decidiu](../quem-decidiu/) (quem propôs, quem votou e quem aprovou cada decisão) é a primeira aplicação e fica em outra pasta (depois, outro repositório); outras podem usar os mesmos dados.

## Propósito

- **Um só lugar para os dados públicos**, de qualquer poder (legislativo, executivo, judiciário) e esfera (federal, estadual, municipal). Hoje: legislativo federal, Câmara dos Deputados e Senado Federal.
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
| Ingestão (Câmara e Senado) | Funcionando: captura com hash (CSV e JSON), carga no raw (dlt), monitoramento de disponibilidade, colunas e volume; código próprio por fonte só quando preciso |
| Transformação | Funcionando: dbt em camadas, identidade de pessoas, testes de qualidade, catálogo e dicionário de colunas |
| Orquestração | Linha de comando e Dagster, com os ativos gerados a partir de `sources/` |
| Documentos e vetores (esqueleto em `documents/`), camada de consumo em PostgreSQL, infraestrutura | A fazer |

Última carga real (2000 a 2026): 190 mil votações, 1,9 milhão de votos, 886 mil proposições, 7,9 mil pessoas.

## Estrutura

```text
src/plataforma_dados/   core (base), ingestion, transformation, orchestration; um só pacote com extras
sources/                declaração das fontes: sources/<poder>/<esfera>/<fonte>.yml
dbt/                    projeto dbt: staging, intermediate, marts
ddl/                    migrações SQL das tabelas próprias (metadata, identity)
docs/  tests/             documentação e testes
.env.example            modelo das variáveis de ambiente (o `.env` fica fora do git)
```

O fluxo: fonte oficial → `landing` (arquivos com hash) → `raw_<esfera>_<fonte>` (dlt) → `staging` → `intermediate` → `marts` (dbt). Detalhes em [`docs/dados/camadas.md`](docs/dados/camadas.md).

## Como subir o ambiente

Requisitos: Python 3.13 e [uv](https://docs.astral.sh/uv/). A partir desta pasta (`plataforma-dados/`):

```bash
uv sync --all-extras
```

```bash
uv run plataforma run --years 2025 2026
```

Outros modos: `--incremental` (só o que pode ter mudado) e `--historical --from-year 2000` (carga massiva). Os dados ficam em `data_store/` (fora do git).

**Conexões e segredos** vão em variáveis de ambiente: copie `.env.example` para `.env` (fora do git) e use `uv run --env-file .env plataforma ...` (o `dagster dev` já carrega o `.env` da pasta). Em produção, a infraestrutura injeta as variáveis, de preferência a partir de um gerenciador de segredos.

```bash
uv run plataforma query --sql "SELECT * FROM marts.pessoas LIMIT 10"
```

```bash
uv run plataforma docs
```

O último abre o grafo de linhagem e o dicionário de colunas (dbt docs). Para a interface do Dagster:

```bash
uv run dagster dev -m plataforma_dados.orchestration.definitions
```

Antes de abrir um PR:

```bash
uv run ruff check . && uv run ruff format --check . && uv run mypy && uv run pytest
```

## Onde ler mais

| Quero... | Leia |
| --- | --- |
| ver as camadas e como executar | [`docs/dados/camadas.md`](docs/dados/camadas.md) |
| saber quais tabelas e colunas existem | [`docs/dados/catalogo.md`](docs/dados/catalogo.md) |
| acrescentar uma fonte | [`docs/dados/especificacao-de-fonte.md`](docs/dados/especificacao-de-fonte.md) |
| ver o que falta e o que cada fonte não entrega | [`docs/dados/cobertura-e-lacunas.md`](docs/dados/cobertura-e-lacunas.md) |
| entender a ligação de pessoas entre fontes | [`docs/dados/identidade-de-pessoas.md`](docs/dados/identidade-de-pessoas.md) |
| entender a Câmara e como se vota | [`docs/dominio/camara-dos-deputados.md`](docs/dominio/camara-dos-deputados.md) |
| ver por que cada decisão foi tomada | [`docs/adr/`](docs/adr/) |
| trabalhar com IA neste repositório | [`AGENTS.md`](AGENTS.md) |

Índice completo em [`docs/README.md`](docs/README.md). O trabalho é conduzido em itens pequenos no quadro do GitHub Projects.

## Como contribuir

Ainda não recebemos contribuições de código. Para sugerir correção de dado, abra uma issue com o link da fonte oficial.
