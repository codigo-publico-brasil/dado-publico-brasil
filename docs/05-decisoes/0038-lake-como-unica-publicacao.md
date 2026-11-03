# ADR 0038: o lake é a única publicação; sem PostgreSQL de serviço e cada aplicação monta as suas consultas

- **Status:** proposto (2026-11-03); decisão do fundador na conversa de 03/11/2026
- **Data:** 2026-11-03
- **Substitui:** [ADR 0014](0014-warehouse-lake-duckdb-e-postgres-de-servico.md) (a parte do PostgreSQL de serviço) e [ADR 0034](0034-manter-duckdb-e-postgres.md) (manter o PostgreSQL)
- **Altera:** [ADR 0033](0033-marts-com-a-terminologia-da-dbt-labs.md) (item 2: `marts` deixa de ser publicado no PostgreSQL; o contrato com as aplicações passa a ser o Parquet do lake)

## Contexto

Os marts iam para dois lugares: o lake público em Parquet ([ADR 0035](0035-lakehouse-publico-no-r2.md)) e um PostgreSQL de serviço (`publish`). Nenhuma aplicação lê o Postgres hoje. Além da duplicação, as dez views `app_*` eram copiadas como tabelas, e cada aplicação nova pediria as suas, no esquema de todos. Foi o que quebrou a primeira aplicação: ela precisava de colunas que o repositório de dados só entregou com semanas de atraso, porque três PRs foram mergeadas numa branch errada.

## Decisão

1. **O lake é a única publicação.** O comando `publish`, o serviço PostgreSQL do `compose.yaml`, o do CI e as variáveis de conexão saem. O `export` e o `publish-docs` continuam.
2. **Os marts são o contrato.** Cada aplicação lê o Parquet (ou `catalogo.duckdb`, ou `manifesto.json`) e monta as suas consultas no banco que quiser. Mudança de coluna num mart exige ADR e aviso.
3. **Regra de negócio fica nos marts, nunca na aplicação.** A consulta só junta nomes e filtra. Se uma view `app_*` precisa de regra (suplente, fim real do mandato), a regra vira um `fct_`/`agg_` com teste.
4. **As views `app_*` saem.** Sete foram removidas agora (nenhuma aplicação as lê). Três ficam até a aplicação ter as suas: `app_cargo_ocupantes`, `app_pessoa_campanhas` e `app_pessoas`. Nenhuma `app_*` nova entra. Isso fecha quando a regra de `app_cargo_ocupantes` estiver num mart e as outras duas puderem ser refeitas só sobre os marts.
5. **Cada aplicação testa o contrato no próprio CI:** confere no `manifesto.json` se as colunas de que depende existem. O lake aponta sempre para o dado atual, sem versão por data; o teste é o que pega a mudança antes da produção.

## Alternativas consideradas

- **Manter o PostgreSQL só com as `app_*`:** corta a duplicação, mas mantém o repositório de dados responsável pelo formato de consumo de cada aplicação, sem dono nem prazo para sair.
- **Uma pasta de Parquet por aplicação:** cada aplicação vira uma cópia a gerar, publicar e manter sincronizada. O lake público já entrega o Parquet; o que a aplicação precisar pré-juntado, ela gera no próprio CI.
- **DuckLake ou outro catálogo transacional:** já avaliado e descartado no ADR 0034; nada mudou.

## Consequências

- Menos infraestrutura: sem banco, sem papéis, sem troca atômica de esquema e sem a armadilha de uma consulta pesada segurar o `publish`.
- Quem precisa de baixa latência ou de consulta concorrente traz o seu banco e carrega o Parquet numa rotina agendada. Ler o lake por HTTP a cada requisição não é o uso pretendido.
- Sem papéis de leitura, vale o que já vale para o lake: tudo o que está lá é público.
- **Gatilho para reabrir:** uma aplicação exigir consulta concorrente com baixa latência sobre os marts que ela não consiga resolver com cópia própria. O desenho antigo está no ADR 0014.
