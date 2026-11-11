# ADR 0046: publicação tolerante a falhas de nós isolados e raw sempre presente

- **Status:** aceito em 2026-11-11 (implementado; antes proposto (2026-11-06), para revisão do fundador)
- **Data:** 2026-11-06
- **Altera:** o item 6 do [ADR 0035](0035-lakehouse-publico-no-r2.md) ("publicação só depois dos testes do dbt": de tudo-ou-nada para por tabela) e os itens 2 e 6 do [ADR 0042](0042-ciclo-noturno-de-processamento-e-publicacao.md) (a publicação sai do job `processar_tudo` e passa a ser uma execução própria).

## Contexto

No ciclo de 06/11/2026 quatro nós do dbt (dois modelos e dois testes de `transparencia`) falharam por uma causa independente do resto: as tabelas do raw de datasets recém-declarados nunca tinham sido criadas (nenhuma captura). Como `dbt_post_identity` é um passo só, o Dagster o marcou como falho, pulou o `export` e as docs, e o lake inteiro deixou de ser publicado por causa de quatro nós. Na mesma madrugada a captura da Câmara abortou no primeiro dataset com erro (mudança de chave para `_row_hash` sobre tabela já carregada), e os demais datasets da fonte nem carregaram.

## Decisão

1. **Raw sempre existe.** Todo dataset `raw: true` ganha a tabela no raw, vazia, antes de qualquer leitura do dbt: no início de `load_pending` e antes do `dbt_pre_identity` (e do comando `transform`). Usa o mesmo recurso do dlt da carga (`dlt.mark.materialize_table_schema()`, [documentação do dlt](https://dlthub.com/docs/general-usage/resource)), com as mesmas colunas, tipos, chave e colunas internas, então a carga seguinte não muda o esquema. Os modelos rodam com zero linhas e os testes de lacuna medem a ausência.
2. **Mudança de chave não falha a carga.** Se a tabela existente não tem uma coluna da chave do contrato, o `load_pending` descarta o dataset (e o estado do dlt) e recarrega as capturas vigentes do landing (o raw é espelho do landing: nada se perde), e registra `recarga_por_chave` em `metadata.fontes_verificacoes`. Um dataset que falha por qualquer motivo é registrado (`carga` em erro, visível na verificação `saude_da_fonte` e no sensor `verificacoes_em_erro`) e os demais da fonte seguem; as capturas dele ficam pendentes e tentam de novo na próxima carga.
3. **O passo do dbt não falha por nó em erro.** Os passos do dbt usam `raise_on_error=False`: o resultado e o tempo de todos os nós (erro, aviso, pulado) são gravados em `metadata.testes_resultados`, sempre (também se o passo for interrompido: gravação em `finally`), e a execução em `metadata.execucoes` fica com `error` e a duração real. A falha fica visível: `context.log.error` por nó na aba Runs, relatório do `observe` e e-mail de `observability.notify`. Falha do dbt sem nenhum nó reprovado (não iniciou, caiu) continua falhando o passo.
4. **Publicação por tabela.** O `export` lê, da última execução de cada fase, os nós reprovados e o manifesto do dbt e **não publica versão nova** da tabela cujo modelo falhou ou foi pulado (entrada a montante em erro), nem da tabela testada por um teste em erro ou falha (`attached_node`; teste singular: todos os modelos de que depende). Essas tabelas ficam com a versão **anterior** no lake (nada é apagado) e o manifesto traz `excluida_por` com o motivo; o catálogo avisa no comentário da view. O restante é publicado normalmente. Corrigido o nó, a execução seguinte volta a publicar e o campo some. Nunca se publica versão nova de tabela com teste de erro falhando.
5. **A publicação é uma execução própria.** O Dagster pula o passo cujo insumo (um ativo dbt) não foi materializado, e um modelo em erro não é materializado: com o `export` dentro de `processar_tudo` (dependente dos marts), um único modelo em erro o pularia. Os jobs que processam (`processar_tudo`, `atualizar_tudo`, `atualizar_<fonte>`) não incluem mais `publicacao/lake` e `publicacao/docs`; o sensor `publicar_apos_processar` pede o job `publicar` quando um deles termina com sucesso. Falha real (identidade, queda do dbt) continua sem publicar.

## Alternativas consideradas

- **Manter tudo-ou-nada (0035 item 6):** a garantia mais simples, mas um nó isolado trava o lake inteiro, como em 06/11. Rejeitada.
- **Exportar tudo mesmo com falha:** publicaria dado reprovado nos testes. Rejeitada: viola a garantia de qualidade.
- **Manter o `export` no job e tirar as dependências dos marts:** perde a ordem garantida pelo grafo (depende de prioridade de execução) e continua pulando o passo se qualquer insumo faltar. Rejeitada.
- **Raw vazio criado por `dbt` (macro) em vez de pelo dlt:** esquema duplicado em dois lugares, divergência com a carga. Rejeitada.

## Consequências e riscos

- **Dado antigo publicado por mais tempo** quando um nó falha. Como se vê: `excluida_por` no `manifesto.json`, aviso no comentário da view do catálogo, `erro` na aba Runs, no `observe` e no e-mail. O público consegue auditar; o dado nunca é novo e errado.
- **Falha de modelo `pre_identity` ainda pula o `dbt_post_identity` inteiro** no Dagster (o passo depende das saídas daqueles modelos). A publicação ocorre, com o que passou; os marts ficam na versão anterior. Reduzir isso exige desligar dependências entre as fases no tradutor; fica como melhoria.
- **Um ciclo cuja publicação falha** deixa `publicacao/docs` desatualizado e o ciclo seguinte reprocessa; a mitigação é relançar o job `publicar`.
- Dataset com recarga por mudança de chave grava de novo as linhas do landing (custo de tempo proporcional ao dataset).
- O comando de linha de comando `transform`/`run` continua parando no primeiro erro do dbt (modo interativo, falha rápida); o `export` aplica o mesmo filtro por tabela.
