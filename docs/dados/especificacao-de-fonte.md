# Declaração de fonte (`sources/<poder>/<esfera>/<fonte>.yml`)

Referência do arquivo (na pasta `sources/` da raiz) que descreve uma fonte oficial: de onde receber, o que carregar e como carregar no raw. Quem o lê é o código de ingestão, e quem grava as tabelas é o dlt. **O contrato não transforma nada**: renomear, converter tipos e padronizar texto é trabalho do dbt (camada staging). O exemplo completo é [`sources/legislativo/federal/camara.yml`](../../sources/legislativo/federal/camara.yml).

## Estrutura

```yaml
source: camara                      # nome curto: prefixo dos modelos stg_camara__* e valor da coluna `fonte`
power: legislativo                  # legislativo | executivo | judiciario
level: federal                      # federal | estadual | municipal: o raw vira raw_federal_camara
description: Câmara dos Deputados, dados abertos (arquivos em lote)

access:
  base_url: https://dadosabertos.camara.leg.br/arquivos
  format: csv
  delimiter: ";"
  encoding: utf-8-sig               # com BOM

datasets:
  proposicoes:                      # um dataset = um arquivo (full) ou um por ano (yearly)
    url: "{base_url}/proposicoes/csv/proposicoes-{year}.csv"
    load: yearly                    # full | yearly
    first_year: 2001                # (yearly) primeiro ano publicado pela fonte: anos anteriores não são pedidos
    stable_after_years: 1           # (yearly) anos mais antigos que isso não mudam: a carga incremental os pula
    extra_years: true               # (yearly) aceita anos só deste dataset (--extra-years)
    write: merge                    # merge (upsert pela chave) | replace (troca o conteúdo anterior)
    primary_key: [id]
    columns: [id, siglaTipo, numero, ano, ementa, dataApresentacao]   # lista permitida
```

## Regras

- **`columns` é a lista permitida.** Só estas colunas do arquivo são lidas (minimização de dados, princípio IX). O nome é o do arquivo; o dlt o normaliza para snake_case (`siglaTipo` vira `sigla_tipo`).
- **Documentos pessoais são recusados.** Um contrato que liste `cpf`, `rg`, `titulo_eleitor`, `cnh` ou `passaporte` não carrega. Um teste confere.
- **`write: merge` exige `primary_key`**; linhas sem valor na chave são rejeitadas e contadas. `write: replace` serve a arquivos completos que substituem o anterior.
- **Valores como texto, vazio como nulo.** Tipos e limpeza ficam no staging.
- Toda linha do raw leva `_source_file_id`, o id da captura (arquivo do landing) de onde veio.
- Erros do contrato (tipo, chave ou `load` inválidos) dizem onde está o problema.

## Receitas

**Acrescentar uma coluna:** uma linha em `columns`. Na próxima carga o dlt cria a coluna (linhas antigas ficam vazias até `load --rebuild`). Para usá-la, acrescente-a ao modelo de staging e, se for exibida, ao mart e ao seu `schema.yml` (o contrato do mart falha se faltar).

**Remover uma coluna:** apague de `columns` e rode `load --rebuild`; o dlt recria a tabela do landing. O `dbt build` acusa os modelos que a usavam.

**Mudar a URL da fonte:** `access.base_url` (ou o `url` do dataset). A captura antiga continua no landing e em `metadata.captures`.

**Mudar a pasta dos dados ou o warehouse:** variáveis `PLATAFORMA_STORAGE_ROOT` e `PLATAFORMA_WAREHOUSE`.

**Fonte nova:**

1. Criar `sources/<poder>/<esfera>/<fonte>.yml` (a fonte é encontrada pela pasta; não há registro a fazer).
2. Escrever o `_<fonte>__sources.yml` e os modelos `stg_<fonte>__*.sql` (um por tabela do raw) em `dbt/models/staging/<fonte>/`.
3. Escrever os modelos de intermediate que unem a fonte às entidades do projeto, e a ligação de identidade (`identity/`), com a regra de ligação conservadora ([identidade de pessoas](identidade-de-pessoas.md)).
4. Declarar descrição, `meta` (sensibilidade, grain, dono) e testes no YAML do dbt; rodar `catalog` e conferir `docs/dados/catalogo.md`.
5. Testes: o modelo é `tests/test_landing_and_loader.py` (fonte fictícia só com contrato) e `tests/test_marts.py` (conjunto sintético da Câmara).
