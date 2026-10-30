# Declaração de fonte (`sources/<poder>/<esfera>/<fonte>.yml`)

Referência do arquivo (na pasta `sources/` da raiz) que descreve uma fonte oficial: de onde receber, o que carregar e como carregar no raw. Quem o lê é o código de ingestão, e quem grava as tabelas é o dlt. **O contrato não transforma nada**: renomear, converter tipos e padronizar texto é trabalho do dbt (camada staging). O exemplo completo é [`sources/legislativo/federal/camara.yml`](../../sources/legislativo/federal/camara.yml).

## Estrutura

```yaml
source: camara                      # nome curto: prefixo dos modelos stg_camara__* e valor da coluna `fonte`
power: legislativo                  # legislativo | executivo | judiciario
level: federal                      # federal | estadual | municipal: o raw vira raw_federal_camara
description: Câmara dos Deputados, dados abertos (arquivos em lote)
schedule: "0 6 * * *"             # quando capturar (cron, fuso America/Sao_Paulo); sem esta linha, só quando pedido

access:
  base_url: https://dadosabertos.camara.leg.br/arquivos
  format: csv                       # csv | json | html (html exige `records` no módulo próprio) | members (lista os arquivos de dentro do zip, com `member` como padrão do nome; guarda `member` e `size`, sem ler o conteúdo)
  delimiter: ";"                    # (csv)
  encoding: utf-8-sig               # com BOM
  headers: {}                       # cabeçalhos HTTP; aceita ${VARIAVEL} do ambiente (credenciais)

datasets:
  proposicoes:                      # um dataset = um arquivo (full) ou um por ano (yearly)
    url: "{base_url}/proposicoes/csv/proposicoes-{year}.csv"
    load: yearly                    # full | yearly
    first_year: 2001                # (yearly) primeiro ano publicado pela fonte: anos anteriores não são pedidos
    extra_years: true               # (yearly) aceita anos só deste dataset (--extra-years)
    write: merge                    # merge (upsert pela chave) | replace (troca o conteúdo anterior)
    primary_key: [id]
    columns: [id, siglaTipo, numero, ano, ementa, dataApresentacao]   # lista permitida
```

## Fonte em JSON (API REST)

O [Senado](../../sources/legislativo/federal/senado.yml) é o exemplo. Mudam três coisas em relação ao CSV:

```yaml
access: {base_url: https://legis.senado.leg.br/dadosabertos, format: json, headers: {Accept: application/json}}
datasets:
  votacoes:
    url: "{base_url}/votacao?dataInicio={year}-01-01&dataFim={year}-12-31"   # a janela vai na URL
    records: ListaX.Itens          # caminho (com pontos) da lista de registros; vazio se o JSON já é a lista
    nested: [votos]                # campos que são listas: viram tabelas filhas no raw (`votacoes__votos`)
    columns: [codigoSessaoVotacao, informeLegislativo__siglaColegiado, votos]   # objetos aninhados viram a__b
```

Os campos que não são listas entram como texto. O raw é fiel: `votacoes` e `votacoes__votos` ligam-se por `_dlt_parent_id = _dlt_id`.

## Pacote `.zip`, anos por passo e minimização

O [TSE](../../sources/judiciario/federal/tse.yml) é o exemplo:

```yaml
  candidaturas:
    url: "{base_url}/consulta_cand/consulta_cand_{year}.zip"
    load: yearly
    first_year: 1996
    step: 2                     # um ano sim, outro não a partir de first_year (eleições gerais e municipais)
    archive: zip                # o landing guarda o pacote original; o leitor lê o membro dentro dele, sem extrair
    member: "*_BRASIL.csv"      # padrão (glob) do nome do membro
    write: merge
    primary_key: [ANO_ELEICAO, CD_ELEICAO, SG_UE, SQ_CANDIDATO, NR_TURNO]   # chave natural: recarregar atualiza a linha
    columns: [...]              # a lista permitida: CPF, título e e-mail não estão nela
    optional: [SG_FEDERACAO, DS_COMPOSICAO_FEDERACAO]   # colunas que os arquivos antigos não têm
```

`columns` filtra as colunas (minimização: o que não está na lista nunca entra no raw). `only: {COLUNA: [valores]}` filtra as linhas **do raw** quando a fonte traz o que não se deve guardar (o arquivo original no landing continua inteiro, para auditoria); o TSE não usa `only`, porque todos os cargos entram. `optional` lista colunas que podem faltar nos arquivos de alguns anos (a ausência vira vazio, não erro). `max_age_days` (por exemplo, `14` na votação) faz o `observe` acusar o dataset cuja última verificação passou do prazo. `primary_key: [_row_hash]` usa o hash da linha inteira como chave, para fontes sem chave natural.

## Dataset por item (`load: foreach`)

Uma chamada para cada linha de outro dataset da mesma fonte. Exemplo (tramitação da Câmara):

```yaml
  proposicoes_tramitacoes:
    url: "https://dadosabertos.camara.leg.br/api/v2/proposicoes/{item}/tramitacoes"
    load: foreach
    format: json                  # este dataset em JSON, mesmo que a fonte seja CSV
    headers: {Accept: application/json}
    records: dados
    foreach:
      from: proposicoes           # dataset (raw) que dá os itens
      item: id                    # coluna do raw que vai em {item}
      where: "sigla_tipo IN ('PL', 'PEC')"   # filtro SQL opcional
      recent_by: data_apresentacao           # mais recentes primeiro
      version: ultimo_status_data_hora       # mudou: busca de novo (ou refresh_after_days: 30)
      batch_size: 500
    primary_key: [_item, sequencia]          # `_item` é o item de origem; precisa estar em columns
    columns: [_item, sequencia, dataHora, ...]
```

Roda só com `--foreach N` (os N mais recentes que faltam) ou `--foreach all`. Cada lote vai ao landing com a resposta de cada item byte a byte, e `metadata.capture_items` registra status e hash ([ADR 0012](../05-decisoes/0012-dataset-por-item-lotes-com-envelope.md)). Conferir com `dado-publico verify` e `dado-publico coverage`. A taxa é `access.rate_limit` (padrão 4 por segundo).

## Credenciais, arquivo compactado, SOAP, robô

O padrão (HTTP com nova tentativa, CSV e JSON) não tem nada disso, de propósito. Os pontos de extensão existem:

- **Credencial:** coloque `${VARIAVEL}` no `headers` do YAML e a variável no `.env` (nunca o valor no YAML).
- **Qualquer outro jeito de obter ou ler** (pacote `.zip`, XML, SOAP, robô): crie `src/dado_publico_brasil/ingestion/custom/<poder>/<esfera>/<fonte>.py` com `download(url, folder)` (devolve o arquivo, o hash e o tamanho), `head(url)` e/ou `records(file, dataset)`. O que não definir segue o padrão, e o landing continua guardando o arquivo original com hash.

## Regras

- **`columns` é a lista permitida.** Só estas colunas do arquivo são lidas (minimização de dados, princípio IX). O nome é o do arquivo; o dlt o normaliza para snake_case (`siglaTipo` vira `sigla_tipo`).
- **Documentos pessoais são recusados.** Um contrato que liste `cpf`, `rg`, `titulo_eleitor`, `cnh` ou `passaporte` não carrega. Um teste confere.
- **`write: merge` exige `primary_key`**; linhas sem valor na chave são rejeitadas e contadas. `write: replace` serve a arquivos completos que substituem o anterior.
- **Valores como texto, vazio como nulo.** Tipos e limpeza ficam no staging.
- Toda linha do raw leva `_source_file_id`, o id da captura (arquivo do landing) de onde veio, e `_ingested_at`, o instante em que chegou ao raw.
- Erros do contrato (tipo, chave ou `load` inválidos) dizem onde está o problema.

## Receitas

**Acrescentar uma coluna:** uma linha em `columns`. Na próxima carga o dlt cria a coluna (linhas antigas ficam vazias até recarregar a captura). **Atenção com a chave:** se o dataset usa `primary_key: [_row_hash]` (votação e prestação de contas do TSE), acrescentar uma coluna muda o hash de toda linha, e recarregar a captura **duplica** as linhas em vez de atualizá-las; veja as [armadilhas operacionais](04-operar-e-publicar.md#armadilhas-operacionais) antes de recarregar. Em dataset com chave natural a recarga só atualiza. Para usá-la, acrescente-a ao modelo de staging e, se for exibida, ao mart e ao seu `schema.yml` (o contrato do mart falha se faltar).

**Remover uma coluna:** apague de `columns` e rode `load --rebuild`; o dlt recria a tabela do landing. O `dbt build` acusa os modelos que a usavam.

**Mudar a URL da fonte:** `access.base_url` (ou o `url` do dataset). A captura antiga continua no landing e em `metadata.captures`.

**Mudar a pasta dos dados ou o warehouse:** variáveis `DADO_PUBLICO_STORAGE_ROOT` e `DADO_PUBLICO_WAREHOUSE`.

**Fonte nova:**

1. Criar `sources/<poder>/<esfera>/<fonte>.yml` (a fonte é encontrada pela pasta; não há registro a fazer).
2. Escrever o `_<fonte>__sources.yml` e os modelos `stg_<fonte>__*.sql` (um por tabela do raw) em `dbt/models/staging/<fonte>/`.
3. Escrever os modelos de intermediate que unem a fonte às entidades do projeto, e a ligação de identidade (`identity/`), com a regra de ligação conservadora ([identidade de pessoas](../01-entender/05-identidade-de-pessoas.md)).
4. Declarar descrição, `meta` (sensibilidade, grain, dono) e testes no YAML do dbt; rodar `catalog` e conferir `docs/03-consultar/01-catalogo.md`.
5. Testes: o modelo é `tests/ingestion/` (fonte fictícia só com declaração, leitores e `custom`) e `tests/orchestration/` (conjuntos sintéticos da Câmara e do Senado em `tests/support/`).
