# Observabilidade dos dados

Para quem opera a plataforma: como saber, a cada atualização, se algo quebrou na origem, na carga ou na lógica, sem olhar tabela por tabela. Decisão em [ADR 0018](../adr/0018-observabilidade-dos-dados.md).

## Camadas

| Camada | O que pega | Onde fica |
| --- | --- | --- |
| Monitor da fonte | Fonte fora do ar, coluna que sumiu ou apareceu (`schema`, `schema_mudou`), queda de volume | `metadata.source_checks` |
| Balanço da carga | Linhas lidas, filtradas, carregadas, rejeitadas e colisões de chave (`carga`) | `metadata.source_checks` |
| Testes do dbt | Regras de negócio, conciliação entre camadas (`reconciliation`), lacunas conhecidas (`gaps`) | `metadata.dbt_results` |
| Elementary (nos marts) | Volume que cai ou explode, coluna removida ou nova, nulos que aumentam | `metadata.dbt_results` e esquema `elementary` |
| Relatório e alerta | Junta tudo, falha se houver problema e envia por e-mail | `plataforma observe` |

## Como usar

1. **Automático:** ao fim de cada fase de marts (`plataforma transform` ou o Dagster), se houver problema, o relatório sai por e-mail. Configure no `.env` as variáveis `PLATAFORMA_SMTP_*` e `PLATAFORMA_ALERT_TO` (modelo em `.env.example`).
2. **Sob demanda:** `plataforma observe` imprime o relatório (código 1 se houver problema); `plataforma observe --email` também envia, útil para testar o SMTP.
3. **Relatório HTML do Elementary** (histórico dos testes, gráficos de anomalia), com o pipeline parado:
   `uvx --from "elementary-data[duckdb]" edr report --profiles-dir dbt --file-path data_store/.state/observabilidade/report.html`
   (rodar de `plataforma-dados/`, com `PLATAFORMA_WAREHOUSE_FILE` apontando para o warehouse).
4. **Erro:** investigar antes de publicar. **Aviso:** ler; muitas vezes é fato da fonte (por exemplo, arquivos antigos do Senado sem campos opcionais).

## Limites conhecidos

- A anomalia de volume só começa a valer depois de cerca de 7 execuções de histórico.
- Uma coluna nova legítima gera um aviso do `schema_changes` uma vez; depois vira a nova referência.
- O Elementary não enxerga o `raw`: ali valem o balanço da carga e o monitor da fonte.

## Amostragem manual

A máquina não prova que o dado está certo. A cada fonte nova: comparar a contagem do raw com a das linhas dos arquivos, conferir alguns registros contra a página oficial e olhar quem foi filtrado.
