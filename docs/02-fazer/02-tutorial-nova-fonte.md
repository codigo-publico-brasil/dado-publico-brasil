# Tutorial: acrescentar uma fonte, da extração à publicação

Para quem vai trazer uma base nova ao projeto. Responde: que passos seguir, em que ordem, o que conferir em cada um e onde está o detalhe. O formato do YAML da fonte está em [`03-especificacao-de-fonte.md`](03-especificacao-de-fonte.md); a convenção de nomes, em [`../03-consultar/02-convencao-de-nomes.md`](../03-consultar/02-convencao-de-nomes.md). Exemplo seguido aqui: o TSE ([`sources/judiciario/federal/tse.yml`](../../sources/judiciario/federal/tse.yml)).

## Antes de começar

- Ache a fonte **oficial** e a URL de download. Todo dado exibido precisa de fonte, URL e data de captura.
- Meça o tamanho e registre em [`../03-consultar/03-fontes-de-dados.md`](../03-consultar/03-fontes-de-dados.md).
- Decida o que **não** entra: documentos pessoais (CPF, RG, título) nunca. Isso vira a lista `columns` do passo 1.
- Proponha antes de executar (AGENTS.md): fonte nova de um poder ou esfera ainda inexistente pede um ADR.

## 1. Declarar a fonte

Pergunte antes: **quando essa base muda?** Declare `schedule` (cron) com a frequência da conferência: diária para quem atualiza todo dia, semanal para quem muda em datas pontuais (a pergunta barata à fonte evita baixar o que não mudou). Sem `schedule`, a captura é só sob pedido. Detalhes em [`03-camadas.md`](../01-entender/03-camadas.md).

Crie `sources/<poder>/<esfera>/<fonte>.yml` com a URL, o formato e, por dataset, `columns` (lista permitida), `primary_key` e `write`. Não há registro a fazer: a fonte é achada pela pasta. Se a fonte não é CSV/JSON simples (SOAP, robô, zip fora do padrão), acrescente `ingestion/custom/<poder>/<esfera>/<fonte>.py`.

## 2. Extrair e carregar

```bash
uv run dado-publico extract --source <fonte> --years 2024     # baixa para o landing, com hash
uv run dado-publico load --source <fonte>                     # carrega no raw (dlt)
```

Confira: o arquivo está em `data_store/landing/<fonte>/...`, a captura em `metadata.captures`, e a tabela `raw_<esfera>_<fonte>.<dataset>` existe (`dado-publico query`). O raw é fiel à fonte: nada renomeado nem limpo.

## 3. Declarar o raw no dbt

Em `dbt/models/staging/<fonte>/_<fonte>__sources.yml`: descrição da fonte com o link oficial (`meta.url`), frescor (`freshness`) e as tabelas do raw com descrição. Use [`_tse__sources.yml`](../../dbt/models/staging/tse/_tse__sources.yml) de modelo.

## 4. Staging

Um modelo `stg_<fonte>__<entidades>.sql` por tabela do raw, **view**, só renomear, converter tipos e padronizar texto (sem joins). Nomes e prefixos de coluna (`id_`, `dt_`, `fl_`) seguem a convenção de nomes. Descreva cada coluna no `_<fonte>__models.yml`.

## 5. Intermediate e marts

Se a fonte traz entidade nova, crie o mart (nome simples, no plural, um grain por tabela, com contrato de colunas); se completa uma entidade existente, junte-a num modelo `int_...`. Pessoas de fonte nova entram na identidade com a regra conservadora ([`../01-entender/05-identidade-de-pessoas.md`](../01-entender/05-identidade-de-pessoas.md)). Sem dado inventado: faltou, fica vazio, e um teste `warn` mede a lacuna.

## 6. Testes e descrições

Testes de chave no YAML (`unique`, `not_null`, `relationships`); reconciliações com `severity: error` e lacunas com `warn` em `dbt/tests/`. Toda tabela e coluna descrita. Depois:

```bash
uv run dado-publico transform
uv run dado-publico catalog     # regenera docs/03-consultar/01-catalogo.md
```

## 7. Publicar

```bash
uv run dado-publico publish     # copia os marts para o PostgreSQL de serviço
```

Veja [`01-rodar-localmente.md`](01-rodar-localmente.md) para subir o PostgreSQL.

## 8. Testes do repositório, documentação e PR

Os testes seguem o modelo de `tests/ingestion/` e `tests/orchestration/` (fonte sintética em `tests/support/`). Documente a fonte em [`../03-consultar/03-fontes-de-dados.md`](../03-consultar/03-fontes-de-dados.md) e as lacunas em [`04-cobertura-e-lacunas.md`](../03-consultar/04-cobertura-e-lacunas.md). Rode os checks de [`../01-entender/04-ferramentas.md`](../01-entender/04-ferramentas.md) e abra o PR com a seção "autoria da IA".

## Onde mudar cada coisa


| Quero mudar... | Edito... |
| --- | --- |
| a pasta dos dados ou o arquivo do warehouse | variáveis `DADO_PUBLICO_STORAGE_ROOT` e `DADO_PUBLICO_WAREHOUSE` |
| a URL de uma fonte, ou as colunas que se carregam | `sources/<poder>/<esfera>/<fonte>.yml` |
| um jeito de obter ou ler que o padrão não cobre (SOAP, robô, zip) | `src/dado_publico_brasil/ingestion/custom/<poder>/<esfera>/<fonte>.py` |
| uma regra de transformação (nome, tipo, caixa, junção) | o modelo SQL em `dbt/models/` |
| uma regra de limpeza de texto | `dbt/macros/text_functions.sql` |
| um teste de dados | `schema.yml` do modelo ou SQL em `dbt/tests/` |
| a ordem das etapas ou o agendamento | `src/dado_publico_brasil/orchestration/` (Dagster ou `pipeline.py`) |

