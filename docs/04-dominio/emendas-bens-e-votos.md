# Emendas, bens e votos: o que os dados dizem

Para quem quer entender os campos que a plataforma traz sobre dinheiro de emendas e sobre candidatos. As fontes estão no [catálogo de fontes](../03-consultar/03-fontes-de-dados.md) e as decisões, no [ADR 0016](../05-decisoes/0016-bens-votos-e-emendas.md).

## Emenda parlamentar

Parlamentares podem **emendar** o orçamento da União para destinar dinheiro a obras e serviços. Os tipos são: **individual** (de cada deputado ou senador; com finalidade definida ou "transferência especial", que vai direto ao município), **de bancada** (de uma bancada estadual), **de comissão** e **de relator** (o relator-geral do orçamento, conhecida como "orçamento secreto" quando o autor real não era informado). O dinheiro passa por três etapas: **empenhado** (reservado), **liquidado** (o serviço foi entregue e conferido) e **pago**. `fct_emendas` traz um valor por etapa; `fct_emendas_convenios`, os convênios firmados; `fct_emendas_favorecidos`, quem recebeu, mês a mês.

O autor vem pelo **nome e por um código orçamentário**, que não é o código do parlamentar na Câmara ou no Senado: por isso a emenda não é ligada a `pessoas`. Os favorecidos são só pessoas jurídicas e unidades gestoras; o cidadão comum que recebeu algum recurso nunca é publicado.

## Bens declarados

Todo candidato declara seus bens ao registrar a candidatura. `fct_candidaturas_bens` traz cada bem (tipo, descrição e **valor declarado**) das pessoas do projeto. O valor é o que o candidato declarou, sem correção, e muda de uma eleição a outra por compra, venda ou valorização.

## Votos por candidato

A fonte traz os votos de cada candidato por **município e zona eleitoral**. `marts.votacoes_votos_de_candidatos` soma por candidatura: `votos_nominais` inclui qualquer destinação (por exemplo, votos anulados por decisão judicial) e `votos_validos` só os que contaram. O detalhe por município e zona de todos os candidatos fica no staging (`staging.stg_tse__votacao`).

> **Conceito: o que está na tabela é o que o órgão publicou.** A plataforma não calcula riqueza, eficiência ou desempenho de ninguém: entrega os fatos com fonte, data de captura e as lacunas medidas.
