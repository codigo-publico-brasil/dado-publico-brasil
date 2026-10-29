# ADR 0033: uma só camada publicada, o `servico`; os marts migram para `fatos` e `core`

- **Status:** proposto (2026-10-29); decisão do fundador na conversa de 29/10/2026 (opção B)
- **Data:** 2026-10-29
- **Altera:** [ADR 0007](0007-dois-pacotes-e-camadas-de-mercado.md) e [ADR 0014](0014-warehouse-lake-duckdb-e-postgres-de-servico.md) (o que o Postgres de serviço recebe) e conclui o item 11 do [ADR 0030](0030-modelo-de-dados-pessoa-no-centro.md).

Para quem mantém os modelos: responde o que é `servico`, o que é `marts`, e para onde vai cada um.

## Contexto

Hoje duas camadas se dizem "o que o aplicativo lê": `marts` (entidades largas, 39 tabelas, nascidas por pergunta) e `servico` (consultas dos aplicativos). O `servico` lê dos marts (`decisao` usa `votacoes` e `proposicoes`; `pessoas` usa `marts.pessoas`), e o Postgres recebe as duas. Marts como `pessoas`, `mandatos` e `candidaturas` repetem o que `core` e `fatos` já têm. Quem consome não sabe qual é o contrato, e quem mantém não sabe onde um modelo novo entra.

## Decisão

1. **O `servico` é a única camada publicada** no Postgres e o único contrato com os aplicativos. Toda coluna e tabela descrita, como hoje.
2. **O `servico` lê só de `fatos`, `core` e `analise`**, nunca de `marts` nem de `servico`. Um teste confere.
3. **Os marts migram, por domínio**, para o esquema que lhes cabe: o que é acontecimento ou ato datado e com fonte vai para `fatos` (proposições, tramitações, votações, normas, vetos, emendas, autorias); o que é catálogo ou entidade de referência vai para `core` (órgãos, partidos, municípios, legislaturas, frentes, dispositivos da Constituição). Nomes seguem a [convenção](../03-consultar/02-convencao-de-nomes.md).
4. **Sem marts novos**: modelo novo nasce em `fatos`, `core`, `analise` ou `servico`.
5. **O Postgres deixa de receber `marts`** quando o último aplicativo migrar para o `servico`. Até lá os dois são publicados, sem views de compatibilidade, e o `eleitos*` sai junto da migração do site (item 11 do 0030).
6. O esquema `marts` é removido no fim.

## Alternativas

- **Manter os dois papéis** (mart como entidade, servico como consulta): menos trabalho agora, mas deixa dois contratos e a dependência `servico → marts`.
- **Aposentar o `servico` e ficar só com marts:** contradiz o ADR 0030 e volta à dispersão por pergunta.

## Consequências

- Um contrato só para o aplicativo, e uma regra simples para quem escreve modelos.
- Custo: mover cerca de 30 modelos, ajustar contratos e testes, e migrar o aplicativo. É feito por domínio, com a ordem e o estado na issue guarda-chuva.
- Os modelos `servico` que hoje leem marts (`decisao`, `pessoas`) só passam a ler de `fatos` e `core` quando o domínio deles migrar; por isso a regra 2 vale por fase, e o teste lista as exceções que ainda existem.
- Merece ADR próprio, se aparecer: a política de retenção e a linhagem por linha ([issue de linhagem](https://github.com/codigo-publico-brasil/dado-publico-brasil/issues/163)).
