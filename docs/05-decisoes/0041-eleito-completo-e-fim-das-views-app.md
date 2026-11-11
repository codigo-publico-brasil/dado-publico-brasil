# ADR 0041: `fl_eleito` completo em `fct_candidaturas` e fim das views `app_*`

- **Status:** aceito (2026-11-03)
- **Data:** 2026-11-03
- **Altera:** [ADR 0039](0039-marts-como-camada-semantica.md) (o item sobre `fl_eleito`) e [ADR 0055](0055-lake-como-unica-publicacao.md) (item 4).

## Contexto

O ADR 0039 recusou mudar o significado de `fl_eleito` (quebraria consumidores sem aviso) e deixou a distinção em `base_eleicao`; a vencedora derivada só aparecia na view `app_pessoa_campanhas`. Com isso "eleito" tinha duas respostas: uma no mart, outra na view. O ADR 0055 (item 4) mandou as views `app_*` saírem quando a aplicação pudesse viver só dos marts, e a regra de ocupação já está em `fct_cargos_ocupacoes` ([ADR 0040](0040-ocupacao-de-cargo.md)).

## Decisão

1. **`fl_eleito` em `fct_candidaturas` é o eleito completo:** informado pelo TSE ou derivado pela Constituição (`base_eleicao` diz qual). `fl_eleito_informado` guarda o significado antigo, só o que o TSE marca. Medido: 533.912 informados + 120 derivados = 534.032 (antes, só prefeito +119 e presidente +1 mudavam).
2. **Por que muda um significado que o 0039 preservou:** o mesmo conceito ("eleito") não pode ter duas respostas, e o consumidor não refaz regra de negócio (ADR 0039). Sem as views `app_*`, o contrato do consumidor passa a ser `fct_candidaturas`; se o significado ficasse, migrar perderia 120 eleitos em silêncio.
3. **As views `app_*` deixam de existir** (`app_cargo_ocupantes`, `app_pessoa_campanhas`, `app_pessoas`), e o prefixo `app_` sai da convenção de nomes. A ocupação está em `fct_cargos_ocupacoes` e a ficha em `dim_pessoas`; a fonte vem de `metadata/capturas` por `id_captura`.

## Consequências

- Aviso ao app: as `app_*` somem do warehouse e do lake; `fl_eleito` mudou de significado (120 a mais) e `fl_eleito_informado` mantém o antigo. Quem filtrava `base_eleicao` para o derivado continua funcionando.
- Menos um nível de modelos para manter; o teste de lacuna da ficha passa a olhar `dim_pessoas` (`pessoas_sem_dado_que_o_tse_tem`).
- Alternativa recusada: manter as views como compatibilidade. Perpetua a segunda resposta e o dono do formato de consumo seria este repositório (ADR 0055).
