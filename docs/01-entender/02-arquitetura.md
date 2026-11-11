# Arquitetura

Para quem quer entender como o sistema é construído e por quê. Responde: quais são as peças, como conversam, onde fica cada coisa no código e quais alternativas foram descartadas. As camadas do dado estão em [`03-camadas.md`](03-camadas.md); aqui está o desenho do sistema.

## O fluxo

```text
fonte oficial ─► landing ─► raw ─► staging ─► intermediate ─► marts ─► export ─► lake público (R2, Parquet)
                (arquivos   (dlt)   └────────── dbt ──────────┘
                 + hash)
                          identity (Python, entre as duas passadas do dbt)
```

O **DuckDB é só o motor de cálculo**, um arquivo descartável que se refaz do landing. O dado público é o **Parquet no lake**, de caminho estável ([ADR 0035](../05-decisoes/0035-lakehouse-publico-no-r2.md)); as aplicações leem os marts dali e montam as suas próprias consultas ([ADR 0055](../05-decisoes/0055-lake-como-unica-publicacao.md)).

## Onde cada coisa fica

| Onde | O que guarda | Acesso |
| --- | --- | --- |
| Servidor de processamento (1 nó, disco local) | Dagster, ingestão, dbt e o arquivo DuckDB (`raw`, `identity`, `metadata`); fila serial, um escritor | privado; só ele sai à rede para baixar as fontes |
| **Bucket público** (R2, `datalake.codigopublicobrasil.com.br`) | Parquet de `staging`, `intermediate`, `marts` e `metadata.capturas`; `catalogo.duckdb` e `manifesto.json` | leitura anônima, sem listagem; o catálogo enumera os arquivos |
| **Bucket privado** | cópias da identidade (`id_pessoa` não se reconstrói) e `metadata` (capturas, execuções); **nunca público** | só o pipeline; com teste de restauração |

O **landing** (que guarda campos que o raw descarta, como CPF) e os arquivos extraídos ficam **só no disco do servidor**, sem cópia: risco aceito no [ADR 0036](../05-decisoes/0036-r2-privado-fonte-da-verdade-do-que-nao-se-reconstroi.md). Só os arquivos que o contrato manda publicar saem, em `arq_`, no lake público.

Caminhos: `staging/<poder>/<esfera>/<fonte>/<modelo>`, `intermediate/<modelo>`, `marts/<domínio>/<tabela>`, cada um `.parquet` ou, nas tabelas grandes com `meta.particao`, uma pasta `ano=AAAA/part-0.parquet`. Como consumir: [`06-consumir-o-lake.md`](../03-consultar/06-consumir-o-lake.md). Em produção, o provedor é trocável (o código fala S3 e SQL padrão); rede privada, segredos fora do Git, alertas de dados e backup são requisitos, não escolhas fechadas.

## As peças e o motivo de cada uma

| Peça | Papel | Por que esta |
| --- | --- | --- |
| **uv** | instala Python e dependências, roda comandos | um só comando reproduz o ambiente (`uv.lock`) |
| **dlt** | carrega os arquivos do landing no raw | já faz `merge` idempotente e evolução de esquema; evita motor próprio ([ADR 0006](../05-decisoes/0006-adotar-dlt-dbt-e-dagster.md)) |
| **dbt-core** | transforma o raw em staging, intermediate e marts, em SQL, com testes e documentação | SQL declarativo, testes e linhagem prontos |
| **DuckDB** | calcula as transformações e grava o Parquet no R2 (`httpfs`) | um arquivo, sem servidor, rápido para análise ([ADR 0014](../05-decisoes/0014-warehouse-lake-duckdb-e-postgres-de-servico.md), [0035](../05-decisoes/0035-lakehouse-publico-no-r2.md)) |
| **Cloudflare R2** | guarda o lake público (Parquet) e o bucket privado | S3 compatível, sem custo de saída, cache e domínio próprio |
| **Dagster** | ordem, agendamento e linhagem entre etapas | os ativos saem de `sources/`, sem código por fonte |
| **Código próprio** | landing (hash, imutabilidade), identidade de pessoas, auditoria | o que nenhuma ferramenta faz, e é onde mora a garantia do projeto |

Ferramentas e seus comandos: [`04-ferramentas.md`](04-ferramentas.md).

## Escolhas estruturais e alternativas

- **ELT, não ETL.** Guarda-se o dado como veio e transforma-se depois, em SQL. Se uma regra estava errada, corrige-se o SQL e refaz-se, sem baixar tudo de novo. Alternativa: transformar na entrada (perde-se o original e a auditoria).
- **Fontes declarativas.** Uma fonte é um YAML em `sources/<poder>/<esfera>/<fonte>.yml`; só o que o padrão não cobre (SOAP, robô, zip) vira Python em `ingestion/custom/`. Alternativa: um módulo Python por fonte (mais flexível, mais código a manter) ([ADR 0005](../05-decisoes/0005-fontes-declarativas-e-portabilidade.md), [0011](../05-decisoes/0011-buscar-ler-custom-e-chave-por-fonte.md)).
- **Dois motores que só se encontram nos dados.** `ingestion` e `transformation` só importam `core`; só `orchestration` conhece os dois (um teste confere). A fronteira é o schema `raw_<esfera>_<fonte>` e a tabela `metadata.capturas`. Alternativa: um pacote por motor ou um repositório por motor (custo de versionar junto) ([ADR 0009](../05-decisoes/0009-repositorio-de-dados-pacote-unico.md)).
- **Um repositório, um pacote Python com extras.** `uv sync --all-extras` instala tudo; cada motor traz só o que precisa.
- **DuckDB calcula, Parquet público informa.** O DuckDB aceita um escritor por vez, então o pipeline é serializado; ninguém lê o arquivo dele em produção. Alternativas ao Parquet simples: Iceberg no R2 Data Catalog (exige token até para ler) e DuckLake (sem chave primária; dbt não confirmado), ver ADR 0035. Alternativas descartadas: só PostgreSQL, ClickHouse, BigQuery e Snowflake (motivos no ADR 0014).
- **Identidade fora do dbt.** A chave `id_pessoa` não pode mudar depois de entregue; reconstruir do landing não garante as mesmas chaves. Por isso é código com migração e cópia imutável a cada execução.

## Onde ficam os pipelines

Não há uma pasta "pipelines": um pipeline é o **encadeamento** de pastas, guiado por `sources/`.

```text
sources/<poder>/<esfera>/<fonte>.yml   o que capturar (URL, colunas, chaves)           ← declaração
src/dado_publico_brasil/
  core/            configuração, warehouse, execuções, migrações
  ingestion/       buscar, guardar (landing), ler, carregar (raw); custom/ só quando preciso
  transformation/  execução do dbt, identidade, qualidade, catálogo, export (lake), publicação
  orchestration/   liga os dois: comando `dado-publico` e ativos do Dagster
dbt/               modelos SQL: staging, intermediate, marts (+ testes e macros)
ddl/               migrações das tabelas próprias (metadata, identity)
```

Para acrescentar ou mudar um pipeline, edita-se `sources/` (e, se for entidade nova, `dbt/`); `orchestration/` quase não muda. Isso segue a recomendação do Dagster de manter o dbt no mesmo repositório e começar simples, dividindo só quando crescer, e a do dbt Labs de camadas staging, intermediate e marts. Não há motivo, hoje, para uma estrutura de projeto por pipeline.

## Regras que valem em todo o sistema

- O landing nunca é sobrescrito; o resto é reproduzível dele.
- Contratos de dados e testes em cada tabela publicada; teste de erro bloqueia a publicação (o `export` só roda depois dos testes do dbt).
- O landing nunca é público.
- Pipelines idempotentes: rodar duas vezes dá o mesmo resultado.
- Linhagem: toda linha do raw aponta para a captura de origem (URL, hash, data).
