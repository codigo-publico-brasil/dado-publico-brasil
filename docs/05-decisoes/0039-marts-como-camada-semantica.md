# ADR 0039: os marts são a camada semântica; regra de negócio vive neles e a aplicação só consulta

- **Status:** proposto (2026-11-03); desenho aprovado pelo fundador
- **Data:** 2026-11-03
- **Altera:** [ADR 0038](0038-lake-como-unica-publicacao.md) (itens 3 e 4: a regra de `app_cargo_ocupantes` passa a um `fct_`, e a view vira junção pura; as outras duas `app_*` seguem até serem refeitas só sobre os marts).
- **Numeração:** o PR 207 (sobre o qual este empilha) e o PR 208 criaram, cada um, um `0038` diferente. Este usa o próximo número livre depois de conferir as branches e os PRs abertos; resolver a colisão do 0038 é de quem mergeia.

## Contexto

O ADR 0038 fez do lake a única publicação: cada aplicação monta as suas consultas sobre o Parquet dos marts. Isso só funciona se o mart carregar o que uma consulta não deve decidir. Hoje não carrega: a regra "quem ocupa o cargo" (exercício publicado ou mandato, suplente, janela de 31 dias, tipo do mandato, partido na data) estava dentro de `app_cargo_ocupantes`, e uma aplicação nova teria de copiá-la. Faltavam também, nos fatos, chaves de ligação (eleição da candidatura, território e partido do exercício) e a captura de alguns fatos, o que obrigava a consulta a refazer a ligação e escondia a fonte.

## Decisão

1. **Regra de negócio vive nos marts, com teste de dado e unit test.** Uma consulta de aplicação junta nomes e filtra; se precisa de regra, a regra vira coluna ou tabela do mart.
2. **Mudança de mart é aditiva.** Coluna nova entra com descrição, teste e base (`informado` ou `derivado`) quando não vem da fonte; não se muda o significado de coluna existente, nem se renomeia ou remove sem aviso à aplicação. Remover `dim_municipios` e renomear `dim_partidos_camara.id_partido` ficam para depois de avisar o app.
3. **Fato deriva e marca.** `fct_candidaturas` ganha `id_eleicao` e `base_eleicao`; `fct_mandatos`, `ano_inicio` e `tipo_mandato`; `fct_exercicios`, `id_candidatura`, `id_territorio`, `id_partido` e `base_partido`; `fct_campanhas`, `dt_captura`; `fct_eventos`, `fonte` e `dt_captura`. Todo valor derivado diz que é derivado; sem prova, fica vazio.
4. **A ocupação de cargo é um fato próprio**, `fct_cargos_ocupacoes` ([ADR 0040](0040-ocupacao-de-cargo.md)), e `app_cargo_ocupantes` passa a ser só junção de nomes sobre ele.

## Alternativas consideradas

- **Deixar a regra na view `app_*`:** cada aplicação nova a reescreve, e a regra diverge sem teste que a una.
- **Uma tabela larga por aplicação no repositório:** é o que o 0038 recusou (o repositório de dados passa a responder pelo formato de consumo de cada app).
- **Mudar o significado de colunas existentes (por exemplo, `fl_eleito` com a regra derivada):** quebra consumidores sem aviso; a coluna `base_eleicao` carrega a distinção sem mexer nela.

## Consequências

- O contrato para as aplicações cresce só por adição; o teste de contrato de cada aplicação (0038, item 5) continua suficiente.
- `app_cargo_ocupantes` mantém colunas e linhas. Única diferença medida no warehouse real: em 152 exercícios sem mandato eleito, o partido passa a ser o do histórico da Câmara quando existe, em vez do último registro até o ano.
- Quando as outras duas `app_*` puderem ser refeitas só sobre os marts, saem, e este ADR se cumpre por inteiro.
