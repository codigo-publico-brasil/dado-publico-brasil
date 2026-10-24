# ADR 0018: Observabilidade dos dados com fotografia e comparação

- **Status:** aceito (2026-10-24, pelo fundador)
- **Data:** 2026-10-24

## Contexto

Os testes do dbt só pegam o que alguém previu. Precisamos achar de forma automática problema de lógica (junção que multiplica ou perde linhas), da origem (formato que muda, arquivo parcial) e da ingestão (linhas rejeitadas).

## Decisão

1. **Cinco camadas:** monitor da fonte (disponibilidade, cabeçalho, volume); balanço da carga (`carga`); testes do dbt, com `reconciliation` e `gaps`; fotografia das tabelas com comparação com a execução anterior; relatório único, `plataforma observe` (código de saída 1 se houver erro).
2. **Fotografia** em `metadata.table_profile` e `metadata.column_profile` (nos marts, nulos e valores distintos) a cada `transform_post`; achados em `metadata.data_checks` (`ok`, `warn`, `error`). Limiares em [`observability.py`](../../src/plataforma_dados/transformation/observability.py).
3. **Nada interrompe o pipeline:** o achado é registrado e o relatório decide.
4. **Não adotamos agora** Elementary, Great Expectations ou Soda: dependência nova sem ADR e sem teste local; o que fazem de essencial (volume, esquema, nulos) está no módulo próprio. Reavaliar em produção, com alertas.

## Consequências

- O primeiro relatório de cada ambiente não tem comparação.
- Variações legítimas (carga nova) geram aviso; o humano decide.
- Amostragem manual continua necessária (ver [observabilidade](../dados/observabilidade.md)).
