# Convenção de nomes e descrições

Para quem cria ou altera tabelas e colunas (pessoas e agentes de IA): como nomear e descrever. Decisão em [ADR 0022](../05-decisoes/0022-convencao-de-nomes-e-descricoes.md). **Leia antes de criar qualquer tabela ou coluna.**

## Tabelas

- **Tema na frente, detalhe depois**, sem conectivos (`de`, `em`, `por`, `do`). Assim as tabelas parecidas ficam juntas na ordem alfabética: `proposicoes`, `proposicoes_autorias`, `proposicoes_tramitacoes`.
- Plural, minúsculas, sem acento, palavras separadas por `_`.
- O nome diz o objeto: `proposicoes_autorias` (autoria de quê?) e não `autorias`.
- Modelos de staging seguem o padrão do dbt, `stg_<fonte>__<tabela>`, e a parte `<tabela>` segue esta regra. Os de intermediate levam `int_`.
- **Nos marts, o prefixo diz o tipo da tabela** (terminologia de Kimball, a que o guia da dbt Labs usa):

  | Prefixo | O que é | Exemplos |
  | --- | --- | --- |
  | `dim_` | dimensão: algo que existe (pessoa, cargo, partido, território, órgão). Se guarda a história por período (SCD tipo 2), usa `dt_inicio`, `dt_fim` e `fl_vigente` na própria tabela, sem outro prefixo | `dim_pessoas`, `dim_partidos` |
  | `fct_` | fato: algo que aconteceu, datado e com a fonte (voto, mandato, candidatura, proposição) | `fct_votos`, `fct_mandatos` |
  | `brg_` | ponte entre duas entidades, quando a relação é muitos-para-muitos | `brg_proposicoes_autorias`, `brg_frentes_membros` |
  | `agg_` | agregado por período, derivado dos fatos | `agg_composicoes` |

  O tema `fontes` (pasta `marts/fontes`) reúne as **medições da publicação das fontes** ([ADR 0054](../05-decisoes/0054-fato-agregado-e-avaliacao.md)): `fct_fontes_ocorrencias` (o que a fonte deixou de entregar e desde quando, com a captura de evidência) e `agg_fontes_<medida>` (uma medida por coluna, sem nota, ranking nem limiar). Tabela `*_fontes_*` traz `fonte`, nunca `id_pessoa`; a descrição diz a unidade, o que entra e o que fica de fora.

  Tabela de entrada curada à mão (seed) que é dimensão leva `dim_` e fica em `marts`; a que só alimenta o dbt (`vinculos_aprovados`, `partidos_eventos`) fica em `intermediate`, sem prefixo. Snapshots do dbt, se vierem, levam `snp_`.
- Tabelas do raw espelham o nome da fonte (ver abaixo).

## Colunas

O **prefixo mostra o tipo** da coluna. Outros tipos não têm prefixo.

| Tipo | Prefixo | Exemplos |
| --- | --- | --- |
| Identificador (chave nossa ou da fonte) | `id_` | `id_pessoa`, `id_proposicao`, `id_norma_posterior` |
| Data ou instante | `dt_` | `dt_nascimento`, `dt_inicio`, `dt_captura` |
| Booleano (flag) | `fl_` | `fl_votacao_secreta`, `fl_contem_dado_pessoal` |
| Código que a fonte usa (não é chave nossa) | `cd_` | `cd_emenda`, `cd_autor`, `cd_funcao` |

Regras:

- **Nunca duplique o tipo no nome:** `dt_nascimento`, jamais `dt_data_nascimento`; `id_pessoa`, jamais `id_pessoa_id`.
- **Não encurte o nome** para colocar o prefixo: `votacao_secreta` vira `fl_votacao_secreta`.
- Minúsculas, sem acento, `_` entre palavras, em português.
- Prefixo novo só com decisão registrada em ADR.
- Texto e número não levam prefixo (`nome`, `sigla`, `qtd_votos`).
- **Sem nome de avaliação** ([ADR 0054](../05-decisoes/0054-fato-agregado-e-avaliacao.md)): nenhuma tabela ou coluna de `intermediate`, `marts`, `identity` ou `metadata` tem `rank`, `ranking`, `score`, `pontuacao`, `indice` ou `posicao` entre as partes do nome (`id_proposicao` passa); `nota` só em coluna de texto (a nota de uma norma). Um teste confere.

## Raw

O raw **espelha a fonte**: guarda os nomes de tabela e de coluna como a fonte publica, sem tratamento. Mesmo assim, tem descrição de tabela e de coluna: a da fonte declarada no dbt, ou um texto que diz só que o campo vem da fonte, como publicado (`dado-publico transform` grava os comentários).

## Chaves do contrato da fonte

As chaves dos YAMLs de `sources/` são termos técnicos e ficam em inglês (`license`, `files.collection`, `partition`), como `load` e `primary_key`; só o conteúdo (nomes de tabela e coluna, descrições) segue esta convenção. Veja a [especificação de fonte](../02-fazer/03-especificacao-de-fonte.md).

## Descrições

**Toda tabela e toda coluna, de todas as camadas, tem descrição** (raw, staging, intermediate, marts, identity e metadata). No dbt, a descrição fica no YAML do modelo; nas tabelas de `ddl/`, em `COMMENT ON`. O `export` grava os mesmos comentários dentro de cada Parquet. A descrição diz o que a coluna significa e, quando for dado da fonte, qual é.

## Auditabilidade

O projeto e os dados gerados precisam ser fáceis de auditar pelo público: cada informação deve poder ser rastreada até a fonte oficial. Por isso:

- **colunas de auditoria ([ADR 0035](../05-decisoes/0035-lakehouse-publico-no-r2.md)):** todo staging de fonte traz `fonte`, `id_captura`, `dt_captura`, `url_fonte` e `sha256_captura`, acrescentadas pela macro `colunas_auditoria()` (junção com `metadata.capturas`); intermediate e todo `dim_`, `fct_` e `brg_` propagam `fonte`, `id_captura` e `dt_captura`. Quem não tem arquivo de fonte próprio (identidade, curadoria, agregado, consulta do aplicativo) declara o motivo em `meta.auditoria_excecao`. `tests/test_names_and_descriptions.py` falha sem isso (a conferência é estrutural, por isso fica no CI e não no dbt);
- o staging expõe **todas** as colunas do raw (teste do dbt `staging_sem_colunas_do_raw`, que roda a cada carga); a que ficar de fora tem o motivo em `meta.colunas_omitidas` (coluna: motivo);
- todo modelo leva em `meta` as chaves `owner` (`Código Público Brasil`), `sensitivity` e `fonte_oficial` (herdadas de `dbt_project.yml` quando iguais);
- tabelas dos marts que trazem dado de fonte têm a fonte, o endereço da fonte e a data de captura;
- padronizar um valor não apaga o original: guarde o valor como a fonte publica quando ele for alterado (por exemplo, a sigla original do partido);
- nenhum nome ou transformação pode esconder de onde a informação veio.

## Camadas, grupos, donos e tags (dbt docs e Dagster)

Uma só configuração por pasta em `dbt/dbt_project.yml` (`+group`, `+tags`, `+meta`) alimenta as duas interfaces; o Dagster lê o grupo do dbt (`get_group_name` em `orchestration/definitions.py`). Nenhum modelo repete isso. Os donos dos grupos estão em `dbt/models/_groups.yml`.

| Camada = grupo | O que são | Dono | Tags | `meta` |
| --- | --- | --- | --- | --- |
| `landing` | arquivos originais (ativo do Dagster) | `team:Código Público Brasil` | `landing`, fonte | URL de origem, licença e catálogo (do contrato da fonte) |
| `raw` | tabelas do dlt (ativos do Dagster) | idem | `raw`, fonte | idem |
| `staging` | `stg_<fonte>__*` | `Código Público Brasil` (grupo dbt) | `staging`, fonte (`camara`, `senado`, `tse`...) | `camada`, `fonte_oficial` |
| `intermediate` | `int_*` | idem | `intermediate` | `camada` |
| `marts` | `dim_`, `fct_`, `brg_`, `agg_` | idem | `marts`, domínio (`legislativo`, `eleicoes`, `pessoas`, `compras`, `executivo`, `territorio`, `fontes`) | `camada`, `dominio` |
| `seeds` | tabelas de apoio (`dbt/seeds/`) | idem | `seeds` | `camada` |
| `identity` | pessoas, identificadores e fusões (Python) | `team:Código Público Brasil` | `identity` | |
| `publicacao` | lake em Parquet e docs no R2 | idem | `publicacao` | |

No **dbt docs** (aba *Details*): `Owner` vem do `group` do modelo (sem grupo, o dbt mostra o dono do objeto no banco, que o DuckDB não tem: ficava vazio); `Tags` vêm de `tags`; `Version` é a versão de modelo do dbt (recurso de contrato com `versions:`), que o projeto não usa e por isso fica vazia. O `meta.owner` aparece na seção *Meta*. O grupo não leva e-mail: o projeto não publica um endereço genérico. No **Dagster**, `owners` aceita só e-mail ou `team:<nome>` ([referência da API](https://docs.dagster.io/api/dagster/assets), `owners` do `@asset`; a versão 1.13.29 valida em `is_valid_owner`); as tags são só o nome (camada e fonte/domínio) e os `kinds` mostram o motor (`python`, `dlt`, `dbt`, `duckdb`, `parquet`). Um teste (`test_dagster_assets_carry_layer_group_owner_tags_and_kinds`) confere o padrão.

## Como renomear

1. Renomeie o modelo ou a coluna no SQL e no YAML do dbt, com a descrição.
2. Atualize testes, `docs/03-consultar/01-catalogo.md` (`uv run dado-publico catalog`) e quem lê o mart (as aplicações).
3. Avise quem consome os dados: renomear um mart quebra as aplicações. Se a mudança for de padrão, registre num ADR novo (o mapa de nomes antigos para novos está no [ADR 0033](../05-decisoes/0033-marts-com-a-terminologia-da-dbt-labs.md)).

## Como é garantido

- Este documento é citado no `CLAUDE.md` e no `AGENTS.md`, que os agentes de IA leem antes de trabalhar, e no modelo de pull request.
- Testes no CI (`tests/test_names_and_descriptions.py`) conferem, no warehouse que a pipeline constrói, os prefixos de tipo, os nomes de tabela sem conectivo e a descrição de toda tabela e coluna. A regra vale para staging, intermediate, marts, `identity` e `metadata` (nomes em português desde a migração `ddl/0007_nomes_em_portugues.sql`); o raw espelha a fonte; o esquema `elementary` é do pacote do Elementary e fica de fora.
