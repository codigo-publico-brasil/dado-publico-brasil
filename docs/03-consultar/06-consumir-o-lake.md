# Consumir o lake público

Para quem quer **consultar ou auditar** os dados sem rodar o pipeline (jornalistas, pesquisadores, outras aplicações). Responde: onde estão os arquivos, como ler no DuckDB, em Python e em outras ferramentas, e como conferir que o arquivo é o que foi publicado. Decisão: [ADR 0035](../05-decisoes/0035-lakehouse-publico-no-r2.md). Quem publica está em [operar e publicar](../02-fazer/04-operar-e-publicar.md).

## O que existe

Tudo é Parquet (ZSTD) em `https://datalake.codigopublicobrasil.com.br` (a página inicial resume o lake e linka as docs), sem login. O caminho de toda noite aponta sempre para o dado atual (e `versoes/AAAA-MM/` guarda a versão mensal citável, seção abaixo):

| Caminho | Conteúdo |
| --- | --- |
| `staging/<poder>/<esfera>/<fonte>/<modelo>` | a base tratada de cada fonte (nomes e tipos padronizados); a árvore é a de `sources/` (ex.: `staging/legislativo/federal/camara/...`) |
| `intermediate/<modelo>` | passos intermediários da derivação |
| `marts/<domínio>/<tabela>` | o que se consome (contrato de colunas); domínio = `legislativo`, `eleicoes`, `pessoas`, `territorio`, `compras`, `fontes` |
| `metadata/capturas` | URL, hash SHA-256 e data de cada arquivo capturado da fonte |
| `metadata/fontes_verificacoes` | cada verificação das fontes (disponibilidade, bloqueio, integridade do arquivo, esquema, volume, carga) com resultado e detalhe: o histórico de quando e o que a fonte deixou de entregar |
| `metadata/testes_resultados` | o resultado de cada modelo e teste do dbt em cada execução (inclui os testes de lacuna, que medem o que falta no dado) |
| `staging/<poder>/<esfera>/<fonte>/arq_<coleção>/<caminho>` | **arquivos** que não são tabela (zip original do DOU, fotos dos candidatos), uma pasta `arq_` por coleção; o prefixo `arq_` distingue arquivo de tabela. A lista de cada coleção é a tabela `arq_<coleção>`, no manifesto |
| `<caminho>/<id_execucao>/<nome>.parquet` | onde cada tabela de fato fica: o arquivo é gravado em pasta própria da execução e o manifesto e o catálogo dizem qual é; não monte caminho à mão |
| `<caminho>/<id_execucao>/ano=AAAA/part-0.parquet` | as tabelas grandes que o dbt declara com partição: uma pasta por ano no lugar do arquivo único |
| `catalogo.duckdb` | porta de entrada: uma view por tabela, com descrições |
| `datapackage.json` | o mesmo conteúdo no formato [Frictionless Data Package](https://datapackage.org) (gerado do manifesto): recurso por tabela, esquema, licença, bytes e SHA-256 |
| `versoes/AAAA-MM/` | a **versão datada do mês**: `manifesto.json`, `catalogo.duckdb` e `datapackage.json`, imutáveis ([ADR 0052](../05-decisoes/0052-versao-citavel-do-lake.md)) |
| `manifesto.json` | para quem não usa DuckDB: caminho, arquivos, linhas, bytes, SHA-256, esquema, descrições, `licenca` (da fonte, só no staging), `particao`, `ano` e `camada_medalhao` |

**Equivalência com o medalhão** (os nomes do projeto são os da dbt Labs; o `manifesto.json` traz `camada_medalhao` em cada tabela):

| Medalhão | Aqui |
| --- | --- |
| bronze | landing e `raw` (o `raw` não é público; `metadata/capturas` guarda a origem) |
| prata | `staging` e `intermediate` |
| ouro | `marts` |

Não entram o `raw`, a identidade e o landing (guardam dado pessoal) nem colunas de documento pessoal; do landing saem só os arquivos que a fonte declara publicáveis (seção abaixo). O bucket não lista pastas: por isso o catálogo e o manifesto enumeram os arquivos.

## DuckDB (o jeito mais curto)

```sql
ATTACH 'https://datalake.codigopublicobrasil.com.br/catalogo.duckdb' AS cpb (READ_ONLY);
SHOW ALL TABLES;                                    -- uma view por tabela
SELECT * FROM cpb.marts.dim_pessoas LIMIT 10;
SELECT view_name, comment FROM duckdb_views() WHERE database_name = 'cpb' AND comment IS NOT NULL;
SELECT * FROM cpb.metadata.exportacao;              -- execução, data e commit (`versao_commit`) desta publicação
```

O DuckDB lê só os trechos dos arquivos de que a consulta precisa (filtros e colunas), então não é preciso baixar tudo. Tabelas com `particao` no `manifesto.json` têm a coluna `ano` (e, se grandes, uma pasta por ano): filtre por ela e o DuckDB só abre os anos pedidos. Pela view do catálogo, `WHERE ano = 2022`. Direto nos arquivos, com o curinga e `hive_partitioning`:

```sql
-- exemplo: fct_candidaturas, que vem por ano (veja `particao` e `ano` dela no manifesto; `arquivo` dá o caminho exato):
SELECT count(*) FROM read_parquet('https://datalake.codigopublicobrasil.com.br/<arquivo do ano 2022 no manifesto>');
-- ou, em disco/S3 com listagem: read_parquet('.../fct_candidaturas/**/*.parquet', hive_partitioning = true) WHERE ano = 2022
```

`ano` é o ano inteiro da expressão `particao` (nunca o dia), declarada no dbt: nas candidaturas, resultados e campanhas é o ano da eleição; na votação, nos bens e nas receitas e despesas do TSE, `ano_eleicao`; nos votos, o ano do voto; nas proposições, o ano da apresentação. Só vira pasta por ano a tabela que passa de cerca de 128 MB comprimida; as menores ficam num arquivo só.

**A descrição vai dentro de cada Parquet**, sem arquivo à parte: no rodapé estão `descricao` (da tabela) e `descricoes_colunas` (JSON nome -> descrição, sem colunas de documento pessoal). Ex.: `SELECT key, value FROM parquet_kv_metadata('<arquivo do manifesto>')`, ou `pyarrow.parquet.read_metadata(arq).metadata`. Iguais ao `COMMENT` do catálogo.

As tabelas pequenas com `particao` vêm num arquivo só, ordenado pelo período (o Parquet pula grupos pelas estatísticas). Para um arquivo avulso, use o `arquivo` dele no manifesto.

## Arquivos (`arq_`)

Pasta que começa com `arq_` é uma coleção de arquivos; todo o resto é Parquet. Cada coleção tem uma tabela de controle com um arquivo por linha: `caminho` (relativo à pasta), `sha256_arquivo`, `qtd_bytes`, `content_type`, `fl_original` (verdadeiro se os bytes são idênticos ao capturado da fonte; falso se foram extraídos de um pacote) e as colunas de auditoria (`fonte`, `id_captura`, `dt_captura`, `url_fonte`, `sha256_captura`, que apontam o arquivo ou pacote de origem). Hoje: `arq_secoes` (DOU) e `arq_fotos` (fotos dos candidatos). Decisão: [ADR 0037](../05-decisoes/0037-arquivos-no-lake-com-prefixo-arq.md).

```sql
-- achar e baixar: a URL do arquivo é a pasta da coleção mais o caminho
SELECT 'https://datalake.codigopublicobrasil.com.br/staging/executivo/federal/dou/arq_secoes/' || caminho AS url, sha256_arquivo
FROM cpb.staging.arq_secoes WHERE caminho LIKE 'secao1/202608/%';
```

`fct_candidaturas.foto_caminho` já traz o caminho completo da foto no lake. Confira o arquivo baixado pelo `sha256_arquivo`; `dado-publico export --verificar` faz isso para o lake inteiro. Os arquivos levam `Cache-Control: public, max-age=86400, must-revalidate` (o caminho é estável, o conteúdo pode mudar).

**Diário Oficial da União:** os zips são o original da Imprensa Nacional, sem modificação, sob a licença CC BY-ND 3.0. Redistribua-os inteiros e cite a **Imprensa Nacional** como fonte (a página inicial do lake traz a atribuição); trecho modificado não pode ser redistribuído. As fotos são do TSE, sob a licença dos dados abertos dele.

## Python, pandas e outras ferramentas

```python
import duckdb

con = duckdb.connect()
con.execute("ATTACH 'https://datalake.codigopublicobrasil.com.br/catalogo.duckdb' AS cpb (READ_ONLY)")
df = con.sql("SELECT * FROM cpb.marts.dim_pessoas").df()  # ou .arrow(), .pl() para pyarrow e Polars
```

Qualquer ferramenta que leia Parquet por HTTP (Polars, Spark, R com `arrow`) serve: pegue a URL (`base` + `arquivo`) no `manifesto.json` ou no `datapackage.json`, que também listam tabelas e descrições sem DuckDB.

## Auditar: o arquivo é o que foi publicado?

Cada arquivo do `manifesto.json` traz `sha256`, `bytes` e `linhas`. Para conferir:

```bash
curl -s https://datalake.codigopublicobrasil.com.br/<arquivo do manifesto> | sha256sum   # compare com o sha256 dele
```

E para ir do dado à fonte oficial: toda linha leva `id_captura`, que aponta para `metadata/capturas` (URL oficial, SHA-256 do arquivo original e data da captura). O arquivo original fica no landing privado; com o hash, a fonte confirma que é o mesmo.

## Proveniência: `metadata/capturas` faz parte do contrato

Os marts não trazem `fonte_url`; trazem `id_captura` (e `dt_captura`), e `metadata/capturas` é a dimensão de proveniência que o consumidor junta para chegar à fonte. As colunas `url`, `sha256` e `dt_captura` dela são contrato, com a mesma estabilidade dos marts. Para exibir a fonte de um dado:

```sql
SELECT c.url, c.dt_captura
FROM dim_pessoas AS p JOIN capturas AS c ON c.id_captura = p.id_captura_tse
```

Mesmo caminho para os demais: `fct_candidaturas.id_captura` e `fct_campanhas.id_captura_receitas|despesas|bens` (arquivos do TSE), `dim_pessoas_cadastro.id_captura` (Câmara ou Senado). Um aplicativo que lê o lake lê a ficha de `dim_pessoas` (atributos já resolvidos, com `fonte_*` ao lado; todas as pessoas do projeto) e junta `dim_pessoas_cadastro` (só Câmara e Senado) para contato, gabinete, redes, situação e falecimento. As campanhas saem de `fct_candidaturas` (`fl_eleito` é o eleito informado ou derivado; `base_eleicao` diz qual), `dim_eleicoes`, `dim_disputas`, `dim_cargos`, `dim_partidos`, `fct_campanhas` e `metadata/capturas`.

## O que a fonte deixou de entregar e desde quando

`marts/fontes/fct_fontes_ocorrencias` traz uma linha por ocorrência (indisponível, bloqueio, arquivo inválido, mudança de esquema, coluna ausente, queda de volume), com a primeira e a última observação e a evidência (`id_verificacao` em `metadata/fontes_verificacoes`; `id_captura` em `metadata/capturas`). É medição da publicação, sem nota nem ranking ([ADR 0054](../05-decisoes/0054-fato-agregado-e-avaliacao.md)). O que está em aberto agora:

```sql
SELECT fonte, dataset, particao, tipo_ocorrencia, dt_primeira_observacao, detalhe
FROM fct_fontes_ocorrencias WHERE fl_em_aberto ORDER BY dt_primeira_observacao
```

`agg_fontes_capturas` diz, por dataset, quando veio conteúdo novo pela última vez. O resumo gerado dessas tabelas é [cobertura e lacunas](04-cobertura-e-lacunas.md).

## O que um aplicativo lê

Só os marts do lake e `metadata/capturas`. Não há views `app_*` (o prefixo não existe mais, [ADR 0041](../05-decisoes/0041-eleito-completo-e-fim-das-views-app.md)): cada aplicativo monta as suas consultas, e a regra de negócio já está nos marts (ocupação de cargo em `fct_cargos_ocupacoes`, ficha em `dim_pessoas`, eleito em `fct_candidaturas.fl_eleito`).

## Como citar

Cite a **versão do mês** (`AAAA-MM`), não o caminho de toda noite: ela não muda. Em `https://datalake.codigopublicobrasil.com.br/versoes/AAAA-MM/` estão o `manifesto.json` (o SHA-256 de cada arquivo), o `catalogo.duckdb` e o `datapackage.json`, e os Parquet que eles citam ficam no bucket nos 12 meses seguintes e, para sempre, se a versão tem DOI (fixada). Passado o prazo sem fixação, o manifesto traz `arquivos_removidos`: a versão ainda descreve os dados e dá o hash, mas os arquivos não estão mais lá ([retenção](../05-decisoes/0052-versao-citavel-do-lake.md#retenção-e-custo)).

Modelo (ajuste a data de acesso; acrescente o DOI do manifesto depositado quando houver):

> Código Público Brasil. *Dado Público Brasil*, versão 2026-11 (id_execucao 20261101T030000Z). Licença CC BY 4.0. https://datalake.codigopublicobrasil.com.br/versoes/2026-11/. Acesso em DD/MM/AAAA.

Para reproduzir um número meses depois, consulte o catálogo da versão e confira os arquivos pelo manifesto:

```sql
ATTACH 'https://datalake.codigopublicobrasil.com.br/versoes/2026-11/catalogo.duckdb' AS v (READ_ONLY);
SELECT count(*) FROM v.marts.dim_pessoas;
```

Se houver DOI, ele aponta para o depósito do `manifesto.json` e do `datapackage.json` da versão (nunca dos dados: o lake tem dado pessoal, [ADR 0050](../05-decisoes/0050-dado-pessoal-publicado-pela-fonte-vem-como-esta.md)); o SHA-256 do manifesto prova que o dado conferido é o citado. O `CITATION.cff` da raiz traz o modelo para ferramentas de referência. Decisão: [ADR 0052](../05-decisoes/0052-versao-citavel-do-lake.md).

## Estabilidade e versionamento

Base: [ADR 0039](../05-decisoes/0039-marts-como-camada-semantica.md) (mudança de mart é aditiva). O projeto usa [versionamento semântico](https://semver.org/lang/pt-BR/), com tag `vX.Y.Z` e o [`CHANGELOG.md`](../../CHANGELOG.md); enquanto a versão for `0.x`, mudança que quebra o contrato sobe a versão menor e é anunciada no changelog.

- **Contrato estável:** nomes de tabelas, colunas, tipos e significado dos marts (`dim_`, `fct_`, `brg_`, `agg_`) e de `metadata/capturas`; o formato do `manifesto.json` (chaves, `sha256`, `particao`, `ano`).
- **Muda sem aviso prévio:** linhas e valores (o dado é o atual, ver Cuidados); `staging` e `intermediate` (publicados para auditoria, não são contrato); colunas e tabelas novas (mudança aditiva, não quebra consulta que nomeia colunas); descrições; ordem de linhas e de colunas; número e tamanho dos arquivos Parquet.
- **Como se avisa:** coluna ou tabela que sai, é renomeada ou muda de significado entra no `CHANGELOG.md` em **Alterado** ou **Removido**, e um ADR a antecede. Sempre que possível a coluna antiga convive com a nova por uma versão (como `fl_eleito_informado`).

## Cuidados

- O caminho de toda noite é o dado **atual**; para citar, use a versão do mês (seção abaixo).
- A publicação é atômica: o catálogo e o manifesto só passam a apontar para os arquivos novos depois que todos foram enviados, então nunca há bytes de duas execuções ao mesmo tempo.
- Sem ranking nem nota: as tabelas trazem o que as fontes publicam, com a origem rastreável.
- **Mudança de significado em `fct_candidaturas.fl_eleito` (novembro de 2026):** antes valia só o eleito que o TSE informa (533.912 candidaturas); agora vale o eleito completo, informado **ou derivado** pela regra da Constituição quando o TSE não informa (por exemplo, o 2º turno de presidente de 2006), 534.032 candidaturas, o mesmo conjunto de `fct_mandatos`. `base_eleicao` (`informado` ou `derivado`) diz a origem e `resultado` segue como o TSE informa. Para o antigo, use `fl_eleito_informado`. Quem lia `fl_eleito` esperando só o informado passa a ver 120 eleitos a mais.
