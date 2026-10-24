# Observabilidade dos dados

Para quem opera a plataforma: como saber, a cada atualização, se algo quebrou na origem, na carga ou na lógica. Decisão em [ADR 0018](../adr/0018-observabilidade-dos-dados.md).

## Camadas

| Camada | O que pega | Onde fica |
| --- | --- | --- |
| Monitor da fonte | Fonte fora do ar, coluna que sumiu ou apareceu (`schema`, `schema_mudou`), queda de volume | `metadata.source_checks` |
| Balanço da carga | Linhas lidas, filtradas, carregadas, rejeitadas e colisões de chave (`carga`) | `metadata.source_checks` |
| Testes do dbt | Regras de negócio, conciliação entre camadas (`reconciliation`), lacunas conhecidas (`gaps`) | `metadata.dbt_results` |
| Fotografia e comparação | Tabela que sumiu, volume que caiu ou explodiu, coluna removida, nulos que aumentaram, valores distintos que colapsaram | `metadata.table_profile`, `column_profile`, `data_checks` |
| Relatório | Resume tudo da última execução | `plataforma observe` |

## Como usar

1. Depois de `plataforma transform`, rode `plataforma observe`. Erro devolve código 1.
2. **Erro:** investigar antes de publicar. **Aviso:** ler; muitas vezes é fato da fonte (por exemplo, arquivos antigos do Senado sem campos opcionais).
3. Em mudança de fonte, o cabeçalho é comparado com a captura anterior do mesmo dataset e partição.

## Amostragem manual

A máquina não prova que o dado está certo. A cada fonte nova: comparar a contagem do raw com a das linhas dos arquivos, conferir alguns registros contra a página oficial e olhar quem foi filtrado.

## Depois

Alertas (e-mail ou chat) sobre erros, e reavaliar ferramentas de mercado em produção.
