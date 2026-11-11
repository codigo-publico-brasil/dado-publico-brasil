# Declaração de fonte (`sources/<poder>/<esfera>/<fonte>.yml`)

Referência do arquivo (na pasta `sources/` da raiz) que descreve uma fonte oficial: de onde receber, o que carregar e como carregar no raw. Quem o lê é o código de ingestão, e quem grava as tabelas é o dlt. **O contrato não transforma nada**: renomear, converter tipos e padronizar texto é trabalho do dbt (camada staging). O exemplo completo é [`sources/legislativo/federal/camara.yml`](../../sources/legislativo/federal/camara.yml).

## Estrutura

```yaml
source: camara                      # nome curto: prefixo dos modelos stg_camara__* e valor da coluna `fonte`
power: legislativo                  # legislativo | executivo | judiciario
level: federal                      # federal | estadual | municipal: o raw vira raw_federal_camara
description: Câmara dos Deputados, dados abertos (arquivos em lote)
# licenca: "CC BY"           # opcional: a licença que a fonte declara (texto curto); vai ao manifesto.json de cada tabela da fonte. Sem licença registrada na doc de fontes, omita
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
    write: merge                    # merge (upsert pela chave) | replace (troca a tabela inteira) | replace_partition (troca as linhas da versão anterior do mesmo arquivo)
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

`columns` filtra as colunas (minimização: o que não está na lista nunca entra no raw). `only: {COLUNA: [valores]}` filtra as linhas **do raw** quando a fonte traz o que não se deve guardar (o arquivo original no landing continua inteiro, para auditoria); o TSE não usa `only`, porque todos os cargos entram. `optional` lista colunas que podem faltar nos arquivos de alguns anos (a ausência vira vazio, não erro). `max_age_days` (por exemplo, `14` na votação) faz o `observe` acusar o dataset cuja última verificação passou do prazo. `rejeitadas_toleradas` declara, por partição, quantas linhas **da própria fonte** sem valor na chave o balanço da carga aceita: `rejeitadas_toleradas: {2004: {limite: 1, justificativa: "linha da fonte sem identificador do deputado"}}`. Até o limite, o registro `carga` de `metadata.fontes_verificacoes` vira `warn` com `tolerada: <justificativa>` no detalhe; acima dele (ou com colisão de chave) volta a ser `error`. A linha continua rejeitada, registrada e contada: nada é completado nem inventado, só se evita um erro permanente e repetido a cada captura. Sem a declaração, nada muda. `on_demand: true` (padrão `false`) tira o dataset do plano incremental e da recuperação de lacunas: ele só é capturado quando pedido (`--years`, `--historical`, `--dataset`, ou o job manual do Dagster em `years`/`historical`), e a falta de partições não vira aviso. Serve para pacotes grandes ou republicados com frequência, como as fotos do TSE; o que já está no landing segue valendo para o raw e o dbt. `primary_key: [_row_hash]` usa o hash da linha inteira como chave, para fontes sem chave natural.

## Arquivos servidos ao público (`arquivos`)

Bloco opcional por dataset para arquivos que não são tabela e que o público deve poder baixar ([ADR 0037](../05-decisoes/0037-arquivos-no-lake-com-prefixo-arq.md)). Sem ele, o arquivo fica só no landing (que pode ter campos pessoais e nunca é público).

```yaml
  secao1:                       # DOU: sem `membro`, o arquivo da captura sobe como está (fl_original = true)
    arquivos: {colecao: secoes, caminho: "{dataset}/{particao}/{nome}", publicar: true}
  fotos_br:                     # TSE: com `membro`, cada membro do zip que casa é extraído (fl_original = false)
    archive: zip
    arquivos:
      colecao: fotos
      membro: '^F?(?P<uf>[A-Z]{2})(?P<sq>\d+)_div\.(?P<ext>jpe?g|png)$'
      caminho: "{particao}/{uf}/{sq}.{ext}"
      publicar: true
```

- `colecao`: a pasta é `arq_<colecao>`. `caminho`: modelo do caminho dentro dela, estável (sem hash nem pasta por versão); campos `dataset`, `particao`, `nome` (nome do arquivo ou do membro; no arquivo capturado, sem o hash que o landing põe) e os grupos nomeados de `membro`.
- `membro` (regex, exige `archive: zip`): só os membros que casam são extraídos.
- `publicar: true` autoriza o `export` a subir a coleção ao lake público, com a tabela `arq_<colecao>`; `false` (padrão) só materializa no disco local.
- A carga materializa a cópia derivada em `<pasta de dados>/arquivos/<poder>/<esfera>/<fonte>/arq_<colecao>/` e anota hash e captura de origem em `metadata.arquivos`. Captura corrompida vira aviso (as demais seguem); membro que some de uma captura nova mantém a última cópia, com a captura de origem anterior. O mesmo código serve a qualquer fonte e tipo de arquivo; formato que o padrão não cobre (SOAP, robô) segue em `ingestion/custom/`.

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

Roda só com `--foreach N` (os N mais recentes que faltam) ou `--foreach all`. Cada lote vai ao landing com a resposta de cada item byte a byte, e `metadata.capturas_itens` registra status e hash ([ADR 0012](../05-decisoes/0012-dataset-por-item-lotes-com-envelope.md)). Conferir com `dado-publico verify` e `dado-publico coverage`. A taxa é `access.rate_limit` (padrão 4 por segundo; ver Cortesia e bloqueio).

## Partição mensal (`partition: month`)

Para fontes que publicam um arquivo por mês (o DOU, e as de transparência do executivo):

```yaml
  despesas:
    url: "{base_url}/despesas/{month}"   # {month} é o valor da partição, AAAAMM (como {year} nos anuais)
    load: yearly
    partition: month
    first_month: 202401                  # primeiro mês publicado; meses anteriores não são pedidos
```

O plano incremental pede o mês em curso **e o anterior**: o mês fechado sem mudança custa só um HEAD, e a virada do mês não perde o fim dele. Um 404 do mês anterior não o torna "indisponível" (só os meses mais antigos viram lacuna sem tentativa eterna).

- **`lag_months: 1`** (só `partition: month`) pede só meses fechados: o "mês em curso" do plano passa a ser o anterior (o portal publica o mês depois de fechado). Um 403 no mês mais recente é "ainda não publicado" (`availability`, sem bloqueio); em mês mais antigo, 403 é bloqueio. [ADR 0045](../05-decisoes/0045-meses-fechados-405-e-pacote-unico.md).
- **Vários datasets, um zip:** URLs que diferem só no fragmento `#` leem o mesmo arquivo; o primeiro dataset baixa e os demais registram a captura apontando para o mesmo arquivo do landing (um GET por mês), se o HEAD diz que não mudou.
- **Mês republicado:** os datasets mensais usam `write: replace_partition` ([ADR 0043](../05-decisoes/0043-raw-em-parquet-substituicao-por-particao-e-logs.md)): a captura nova do mês substitui as linhas da anterior (a URL do mês é a partição), então um mês corrigido pela fonte não deixa linha velha no raw. Cada staging declara o grão em `meta.grain` e o teste `warn` `transparencia_linhas_duplicadas_no_grao` mede as duplicatas que a própria fonte traz.
- **Frequência da conferência:** o plano diário pede os dois últimos meses fechados (dois HEAD por dataset); `max_age_days: 40` evita o alerta de defasagem. Um intervalo próprio para meses fechados é pendência (hoje seria um `schedule` por dataset, que o contrato ainda não tem).

## Partição por sequência (`partition: sequence`)

Para o arquivo numerado por um período que não é o ano (a legislatura, por exemplo): o YAML declara o calendário e o núcleo só calcula `first_value + (ano - first_year) // years`, sem saber o que o número significa. A URL usa `{partition}` (aceito em todo tipo de partição; `{year}` e `{month}` seguem valendo).

```yaml
    url: "{base_url}/orgaosDeputados/csv/orgaosDeputados-L{partition}.csv"
    load: yearly
    partition: sequence
    sequence: {first_year: 2019, first_value: 56, years: 4}   # a 56ª legislatura começou em 2019 e dura 4 anos
```

Os três campos são obrigatórios, e `sequence` só vale com `partition: sequence`. O valor da partição é o que vai no caminho do landing e na URL. `partition: legislature` e `{legislature}` deixaram de ser aceitos (o contrato os recusa). [ADR 0053](../05-decisoes/0053-nucleo-sem-nomes-de-fonte.md).

## Cortesia e bloqueio

`access.rate_limit` (requisições por segundo, padrão 4; deve ser maior que zero) é o intervalo mínimo entre as requisições do **download padrão** (HEAD e GET do arquivo) da fonte. **Não vale** para `fetch.get` (datasets `foreach`, que têm o próprio intervalo) nem para módulos `custom/` que fazem a própria requisição.

No download padrão, nada é gravado no landing e o resto da fonte é interrompido naquela execução (sem nova tentativa até o próximo agendamento; a verificação `bloqueio` fica como erro em `metadata.fontes_verificacoes` e é zerada quando a fonte volta a responder) se o **GET** devolve HTTP 403, 405 ou 429 ([ADR 0045](../05-decisoes/0045-meses-fechados-405-e-pacote-unico.md) acrescentou o 405), página HTML no lugar do arquivo ou redirecionamento para outro site. Detalhes:

- **HEAD é brando:** qualquer falha do HEAD (403, 405, 429...) vira "sem informação" e o GET decide; só o GET bloqueia.
- **HTML legítimo:** a regra do HTML não vale quando o formato esperado é `html` (`format: html`).
- **Mesmo site:** o redirecionamento só bloqueia se sair do domínio registrável (`www.in.gov.br` para `in.gov.br` passa). Quando o próprio site oficial hospeda os arquivos noutro domínio (o Portal da Transparência redireciona para `dadosabertos-download.cgu.gov.br`), declare-o em `access.redirect_sites: [cgu.gov.br]`; qualquer outro destino segue bloqueado.
- **Download truncado:** se o corpo recebido não tem o tamanho do `Content-Length` da própria resposta, o download falha e é repetido (três tentativas); nada incompleto é gravado no landing. Se persistir, vira `availability` com erro e a próxima execução tenta de novo.

[ADR 0038](../05-decisoes/0038-cortesia-e-bloqueio-na-ingestao.md). Contornar bloqueio (proxy, troca de IP) está fora do projeto: abra uma issue.

## Credenciais, arquivo compactado, SOAP, robô

O padrão (HTTP com nova tentativa, CSV e JSON) não tem nada disso, de propósito. Os pontos de extensão existem:

- **Credencial:** coloque `${VARIAVEL}` no `headers` do YAML e a variável no `.env` (nunca o valor no YAML).
- **Qualquer outro jeito de obter ou ler** (pacote `.zip`, XML, SOAP, robô): crie `src/dado_publico_brasil/ingestion/custom/<poder>/<esfera>/<fonte>.py` com `download(url, folder)` (devolve o arquivo, o hash e o tamanho), `head(url)` e/ou `records(file, dataset)`. O que não definir segue o padrão, e o landing continua guardando o arquivo original com hash.

## Regras

- **`columns` é a lista permitida.** Só estas colunas do arquivo são lidas (minimização de dados, princípio IX). O nome é o do arquivo; o dlt o normaliza para snake_case (`siglaTipo` vira `sigla_tipo`).
- **Documentos pessoais são recusados.** Um contrato que liste `cpf`, `rg`, `titulo_eleitor`, `cnh` ou `passaporte` não carrega. Um teste confere.
- **`write: merge` exige `primary_key`**; linhas sem valor na chave são rejeitadas e contadas. `write: replace` serve a arquivos completos que substituem o anterior.
- **`write: replace_partition`** é para o arquivo que é a **foto completa** de uma partição (o ano de uma eleição, um mês): a captura nova entra e as linhas das capturas anteriores **da mesma URL** saem. Várias partições convivem na mesma tabela (outras URLs nunca são tocadas) e o raw espelha a versão atual; o histórico fica no landing. Não pede coluna de partição: a partição é a própria captura (`_source_file_id`), então vale para qualquer fonte e não muda o esquema. Não compara linha com linha (barato em dezenas de milhões de linhas); `primary_key: [_row_hash]` segue valendo para manter as linhas idênticas da fonte e dar chave ao dbt. Não aceita `nested`. Recarregar a mesma captura é idempotente. Em tabela que já existe não há migração: todas as linhas já levam o id da captura; na próxima captura nova de cada arquivo, as linhas antigas saem (a primeira carga depois de trocar de `merge` para `replace_partition` pode ainda ter linhas de versões que o `merge` somou: o `load --rebuild --dataset` do dataset as limpa) ([ADR 0043](../05-decisoes/0043-raw-em-parquet-substituicao-por-particao-e-logs.md)).
- **Valores como texto, vazio como nulo.** Tipos e limpeza ficam no staging.
- Toda linha do raw leva `_source_file_id`, o id da captura (arquivo do landing) de onde veio, e `_ingested_at`, o instante em que chegou ao raw.
- **Chave desconhecida falha.** Um erro de digitação (`shedule`, `primay_key`) recusa o contrato, com o nome da chave e do arquivo, em vez de virar o valor padrão em silêncio. Chave nova do contrato entra nas listas de `ingestion/contract.py`.
- **`licenca`** é a licença que a própria fonte declara, como [`03-fontes-de-dados.md`](../03-consultar/03-fontes-de-dados.md) a registra; não se inventa. O `export` a leva ao `manifesto.json` nas tabelas de staging da fonte (marts e intermediate misturam fontes e não a levam).
- **Revisão:** um PR em `sources/` executa código: `foreach.where` é SQL rodado sobre o raw, e `${VARIAVEL}` lê o ambiente. Revise-o com o mesmo rigor de um PR em Python.
- Erros do contrato (tipo, chave ou `load` inválidos) dizem onde está o problema.

## Receitas

**Acrescentar uma coluna:** uma linha em `columns`. Na próxima carga o dlt cria a coluna (linhas antigas ficam vazias até recarregar a captura). **Atenção com a chave:** se o dataset usa `primary_key: [_row_hash]` (votação e prestação de contas do TSE), acrescentar uma coluna muda o hash de toda linha, e recarregar a captura **duplica** as linhas em vez de atualizá-las; veja as [armadilhas operacionais](04-operar-e-publicar.md#diagnóstico-sintoma-causa-e-o-que-fazer) antes de recarregar. Em dataset com chave natural a recarga só atualiza. O `_row_hash` é o SHA-256 do JSON da lista de valores das colunas, na ordem de `columns` (o limite entre colunas e o nulo ficam no texto, então ("ab","c") e ("a","bc") não colidem); mudar essa fórmula troca o hash de toda linha e exige recarga. Para usá-la, acrescente-a ao modelo de staging e, se for exibida, ao mart e ao seu `schema.yml` (o contrato do mart falha se faltar).

**Remover uma coluna:** apague de `columns` e rode `load --rebuild`; o dlt recria a tabela do landing. O `dbt build` acusa os modelos que a usavam.

**Mudar a URL da fonte:** `access.base_url` (ou o `url` do dataset). A captura antiga continua no landing e em `metadata.capturas`.

**Mudar a pasta dos dados ou o warehouse:** variáveis `DADO_PUBLICO_STORAGE_ROOT` e `DADO_PUBLICO_WAREHOUSE`.

**Fonte nova:**

1. Criar `sources/<poder>/<esfera>/<fonte>.yml` (a fonte é encontrada pela pasta; não há registro a fazer).
2. Escrever o `_<fonte>__sources.yml` e os modelos `stg_<fonte>__*.sql` (um por tabela do raw) em `dbt/models/staging/<fonte>/`.
3. Escrever os modelos de intermediate que unem a fonte às entidades do projeto, e a ligação de identidade (`identity/`), com a regra de ligação conservadora ([identidade de pessoas](../01-entender/05-identidade-de-pessoas.md)).
4. Declarar descrição, `meta` (sensibilidade, grain, dono) e testes no YAML do dbt; rodar `catalog` e conferir `docs/03-consultar/01-catalogo.md`.
5. Testes: o modelo é `tests/ingestion/` (fonte fictícia só com declaração, leitores e `custom`) e `tests/orchestration/` (conjuntos sintéticos da Câmara e do Senado em `tests/support/`).
