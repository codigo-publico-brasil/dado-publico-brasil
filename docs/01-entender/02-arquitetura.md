# Arquitetura

Para quem quer entender como o sistema é construído e por quê. Responde: quais são as peças, como conversam, onde fica cada coisa no código e quais alternativas foram descartadas. As camadas do dado estão em [`03-camadas.md`](03-camadas.md); aqui está o desenho do sistema.

## O fluxo

```text
fonte oficial ─► landing ─► raw ─► staging ─► intermediate ─► marts ─► publish ─► PostgreSQL ─► aplicações
                (arquivos   (dlt)   └────────── dbt ──────────┘       (copia      (só leitura)
                 + hash)                                                os marts)
                          identity (Python, entre as duas passadas do dbt)
```

Tudo roda em **um arquivo DuckDB** (o warehouse); o PostgreSQL só recebe os marts já prontos. Desenho de produção, sem fixar provedor: [`arquitetura-producao.html`](arquitetura-producao.html).

## As peças e o motivo de cada uma

| Peça | Papel | Por que esta |
| --- | --- | --- |
| **uv** | instala Python e dependências, roda comandos | um só comando reproduz o ambiente (`uv.lock`) |
| **dlt** | carrega os arquivos do landing no raw | já faz `merge` idempotente e evolução de esquema; evita motor próprio ([ADR 0006](../05-decisoes/0006-adotar-dlt-dbt-e-dagster.md)) |
| **dbt-core** | transforma o raw em staging, intermediate e marts, em SQL, com testes e documentação | SQL declarativo, testes e linhagem prontos |
| **DuckDB** | calcula as transformações | um arquivo, sem servidor, rápido para análise ([ADR 0014](../05-decisoes/0014-warehouse-lake-duckdb-e-postgres-de-servico.md)) |
| **PostgreSQL** | serve os marts às aplicações | consulta concorrente, papel somente leitura, índices |
| **Dagster** | ordem, agendamento e linhagem entre etapas | os ativos saem de `sources/`, sem código por fonte |
| **Código próprio** | landing (hash, imutabilidade), identidade de pessoas, auditoria | o que nenhuma ferramenta faz, e é onde mora a garantia do projeto |

Ferramentas e seus comandos: [`04-ferramentas.md`](04-ferramentas.md).

## Escolhas estruturais e alternativas

- **ELT, não ETL.** Guarda-se o dado como veio e transforma-se depois, em SQL. Se uma regra estava errada, corrige-se o SQL e refaz-se, sem baixar tudo de novo. Alternativa: transformar na entrada (perde-se o original e a auditoria).
- **Fontes declarativas.** Uma fonte é um YAML em `sources/<poder>/<esfera>/<fonte>.yml`; só o que o padrão não cobre (SOAP, robô, zip) vira Python em `ingestion/custom/`. Alternativa: um módulo Python por fonte (mais flexível, mais código a manter) ([ADR 0005](../05-decisoes/0005-fontes-declarativas-e-portabilidade.md), [0011](../05-decisoes/0011-buscar-ler-custom-e-chave-por-fonte.md)).
- **Dois motores que só se encontram nos dados.** `ingestion` e `transformation` só importam `core`; só `orchestration` conhece os dois (um teste confere). A fronteira é o schema `raw_<esfera>_<fonte>` e a tabela `metadata.captures`. Alternativa: um pacote por motor ou um repositório por motor (custo de versionar junto) ([ADR 0009](../05-decisoes/0009-repositorio-de-dados-pacote-unico.md)).
- **Um repositório, um pacote Python com extras.** `uv sync --all-extras` instala tudo; cada motor traz só o que precisa.
- **DuckDB calcula, PostgreSQL serve.** O DuckDB aceita um escritor por vez, então o pipeline é serializado; as aplicações nunca leem dele. Alternativas descartadas: só PostgreSQL, ClickHouse, BigQuery e Snowflake (motivos no ADR 0014).
- **Identidade fora do dbt.** A chave `id_pessoa` não pode mudar depois de entregue; reconstruir do landing não garante as mesmas chaves. Por isso é código com migração e cópia imutável a cada execução.

## Onde ficam os pipelines

Não há uma pasta "pipelines": um pipeline é o **encadeamento** de pastas, guiado por `sources/`.

```text
sources/<poder>/<esfera>/<fonte>.yml   o que capturar (URL, colunas, chaves)           ← declaração
src/dado_publico_brasil/
  core/            configuração, warehouse, execuções, migrações
  ingestion/       buscar, guardar (landing), ler, carregar (raw); custom/ só quando preciso
  transformation/  execução do dbt, identidade, qualidade, catálogo, publicação
  orchestration/   liga os dois: comando `dado-publico` e ativos do Dagster
dbt/               modelos SQL: staging, intermediate, marts (+ testes e macros)
ddl/               migrações das tabelas próprias (metadata, identity)
```

Para acrescentar ou mudar um pipeline, edita-se `sources/` (e, se for entidade nova, `dbt/`); `orchestration/` quase não muda. Isso segue a recomendação do Dagster de manter o dbt no mesmo repositório e começar simples, dividindo só quando crescer, e a do dbt Labs de camadas staging, intermediate e marts. Não há motivo, hoje, para uma estrutura de projeto por pipeline.

## Regras que valem em todo o sistema

- O landing nunca é sobrescrito; o resto é reproduzível dele.
- Contratos de dados e testes em cada tabela publicada; teste de erro bloqueia a publicação.
- Pipelines idempotentes: rodar duas vezes dá o mesmo resultado.
- Linhagem: toda linha do raw aponta para a captura de origem (URL, hash, data).
