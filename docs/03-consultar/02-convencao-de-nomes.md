# Convenção de nomes e descrições

Para quem cria ou altera tabelas e colunas (pessoas e agentes de IA): como nomear e descrever. Decisão em [ADR 0022](../05-decisoes/0022-convencao-de-nomes-e-descricoes.md). **Leia antes de criar qualquer tabela ou coluna.**

## Tabelas

- **Tema na frente, detalhe depois**, sem conectivos (`de`, `em`, `por`, `do`). Assim as tabelas parecidas ficam juntas na ordem alfabética: `proposicoes`, `proposicoes_autorias`, `proposicoes_tramitacoes`.
- Plural, minúsculas, sem acento, palavras separadas por `_`.
- O nome diz o objeto: `proposicoes_autorias` (autoria de quê?) e não `autorias`.
- Modelos de staging seguem o padrão do dbt, `stg_<fonte>__<tabela>`, e a parte `<tabela>` segue esta regra.
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

## Raw

O raw **espelha a fonte**: guarda os nomes de tabela e de coluna como a fonte publica, sem tratamento. Mesmo assim, tem descrição de tabela e de coluna: a da fonte declarada no dbt, ou um texto que diz só que o campo vem da fonte, como publicado (`dado-publico transform` grava os comentários).

## Descrições

**Toda tabela e toda coluna, de todas as camadas, tem descrição** (raw, staging, intermediate, marts, identity e metadata). No dbt, a descrição fica no YAML do modelo; nas tabelas de `ddl/`, em `COMMENT ON`. O Postgres de serviço recebe os mesmos comentários no `publish`. A descrição diz o que a coluna significa e, quando for dado da fonte, qual é.

## Auditabilidade

O projeto e os dados gerados precisam ser fáceis de auditar pelo público: cada informação deve poder ser rastreada até a fonte oficial. Por isso:

- tabelas dos marts que trazem dado de fonte têm a fonte, o endereço da fonte e a data de captura;
- padronizar um valor não apaga o original: guarde o valor como a fonte publica quando ele for alterado (por exemplo, a sigla original do partido);
- nenhum nome ou transformação pode esconder de onde a informação veio.

## Como renomear

1. Renomeie o modelo ou a coluna no SQL e no YAML do dbt, com a descrição.
2. Atualize testes, `docs/03-consultar/01-catalogo.md` (`uv run dado-publico catalog`) e quem lê o mart (as aplicações).
3. Registre o nome antigo e o novo em [`renomeacao-dos-marts.md`](../99-historico/renomeacao-dos-marts.md), para quem consome os dados.

## Como é garantido

- Este documento é citado no `CLAUDE.md` e no `AGENTS.md`, que os agentes de IA leem antes de trabalhar, e no modelo de pull request.
- Testes no CI (`tests/test_names_and_descriptions.py`) conferem, no warehouse que a pipeline constrói, os prefixos de tipo, os nomes de tabela sem conectivo e a descrição de toda tabela e coluna. A regra vale para staging, intermediate e marts; o raw espelha a fonte; `identity` e `metadata` são só descritos por enquanto (os nomes em inglês ficam para outra etapa); o esquema `elementary` é do pacote do Elementary e fica de fora.
