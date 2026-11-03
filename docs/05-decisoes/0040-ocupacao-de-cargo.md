# ADR 0040: ocupação de cargo como fato (`fct_cargos_ocupacoes`), com exercício vencendo o mandato

- **Status:** proposto (2026-11-03); desenho aprovado pelo fundador
- **Data:** 2026-11-03
- **Complementa:** [ADR 0039](0039-marts-como-camada-semantica.md) e [ADR 0030](0030-modelo-de-dados-pessoa-no-centro.md) (mandato e exercício como fatos).

## Contexto

Dois fatos descrevem alguém num cargo: o mandato (`fct_mandatos`, nasce da eleição, para todos os cargos) e o exercício (`fct_exercicios`, publicado pela Câmara e pelo Senado, com fim real e suplentes). Responder "quem ocupa o cargo X em tal data" exige juntar os dois sem contar duas vezes, e essa regra morava numa view do aplicativo.

## Decisão

1. **Grão:** um período em que uma pessoa ocupa um cargo num território. Colunas: `id_ocupacao`, `fonte`, `id_pessoa`, `id_cargo`, `id_territorio`, `id_partido` e `base_partido`, `id_candidatura` e `id_exercicio` (vazias quando não se aplicam), `ano_inicio`, `dt_inicio` e `base_dt_inicio`, `dt_fim` e `base_dt_fim` (`informado` ou `previsto`), `base_ocupacao` (`exercicio` ou `mandato`), `id_captura` e `dt_captura`.
2. **Precedência:** o exercício publicado vence; o mandato cobre o resto, por anti-junção em `id_candidatura` (o mandato que um exercício cumpre não gera outra linha). O exercício cumpre o mandato da mesma pessoa e cargo cuja janela contém o início do período, com 31 dias de folga antes da posse (registro antes da posse); sem mandato, é suplente ou eleição suplementar e fica sem `id_candidatura`.
3. **Sem prova, vazio:** eleito de 2026 tem `ano_inicio` 2027 e `dt_inicio` vazia quando nenhuma fonte nem regra dá o dia; `tipo_mandato` só existe com prova do mandato anterior.
4. **Partido:** o da candidatura do mandato; sem ele, o do exercício, informado pelo histórico da Câmara ou derivado do último registro até o ano do início (`base_partido` diz qual).
5. **Limite conhecido:** cargos sem fonte de exercício (vereador, prefeito, governador, presidente, deputado estadual) terminam no fim previsto pela duração do cargo; cassação e renúncia deles não aparecem (issue 162).

## Alternativas consideradas

- **Só `fct_mandatos` com colunas de exercício:** mistura dois grãos (eleição e período) e perde o suplente.
- **Manter a regra na view do aplicativo:** descartado no ADR 0039.
- **Janela maior ou menor que 31 dias:** 31 cobre o registro antes da posse observado; mais que isso arrisca ligar o exercício ao mandato seguinte.

## Consequências

- Uma só tabela responde "quem ocupa o cargo", para qualquer aplicação; o teste de dado cobre chaves, bases e a lacuna de território e partido.
- `base_dt_fim = previsto` nunca é fim real: a aplicação não deve apresentá-lo como tal.
