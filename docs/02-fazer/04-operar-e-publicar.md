# Observabilidade dos dados

Para quem opera a plataforma: como saber, a cada atualização, se algo quebrou na origem, na carga ou na lógica, sem olhar tabela por tabela. Decisão em [ADR 0018](../05-decisoes/0018-observabilidade-dos-dados.md).

## Camadas

| Camada | O que pega | Onde fica |
| --- | --- | --- |
| Monitor da fonte | Fonte fora do ar, coluna que sumiu ou apareceu (`schema`, `schema_mudou`), queda de volume | `metadata.source_checks` |
| Balanço da carga | Linhas lidas, filtradas, carregadas, rejeitadas e colisões de chave (`carga`); linhas de capturas anteriores que a atual não traz (`linhas_removidas`) | `metadata.source_checks` |
| Testes do dbt | Regras de negócio, conciliação entre camadas (`reconciliation`), lacunas conhecidas (`gaps`) | `metadata.dbt_results` |
| Elementary (nos marts) | Volume que cai ou explode, coluna removida ou nova, nulos que aumentam; nas marts com data de evento (`votacoes`, `votacoes_votos`, `proposicoes`, `normas`, `emendas_convenios`), volume por dia com sazonalidade de dia da semana e frescor (a fonte parou de atualizar) | `metadata.dbt_results` e esquema `elementary` |
| Relatório e alerta | Junta tudo, falha se houver problema e envia por e-mail | `dado-publico observe` |
| Dagster | A saúde de cada fonte e da carga aparece como a verificação `saude_da_fonte` de cada tabela do raw (erro vira falha, aviso vira aviso); o sensor `falha_de_execucao` manda e-mail quando qualquer execução falha | interface do Dagster |

## Como usar

1. **Automático:** se uma execução falhar em qualquer passo, o sensor do Dagster manda e-mail com os passos que falharam e o link da execução (`DADO_PUBLICO_DAGSTER_URL`). E ao fim de cada fase de marts (`dado-publico transform` ou o Dagster), se houver problema, o relatório sai por e-mail. Configure no `.env` as variáveis `DADO_PUBLICO_SMTP_*` e `DADO_PUBLICO_ALERT_TO` (modelo em `.env.example`).
2. **Sob demanda:** `dado-publico observe` imprime o relatório (código 1 se houver problema); `dado-publico observe --email` também envia, útil para testar o SMTP.
3. **Relatório HTML do Elementary** (histórico dos testes, gráficos de anomalia), com o pipeline parado: `dado-publico observe --html` roda o `edr report` por `uvx` (precisa do [uv](https://docs.astral.sh/uv/)) e grava em `data_store/.state/observabilidade/report.html` (cerca de 13 MB). Com `--email`, o arquivo vai anexado. O alerta automático do fim da fase de marts não anexa o relatório, porque o `edr` precisa do warehouse livre.
4. **Erro:** investigar antes de publicar. **Aviso:** ler; muitas vezes é fato da fonte (por exemplo, arquivos antigos do Senado sem campos opcionais).

## Limites conhecidos

- Nas marts sem data de evento, a anomalia de volume só começa a valer depois de cerca de 7 execuções de histórico. Nas cinco com data, o histórico vem do próprio dado.
- Recesso do Congresso (julho e dezembro a janeiro) pode gerar aviso de volume e de frescor: é esperado, e o aviso é só informação.
- O `merge` do dlt não apaga: uma linha que a fonte removeu continua no raw. O aviso `linhas_removidas` conta as que vieram de capturas anteriores do mesmo arquivo e a atual não traz; decidir o que fazer com elas é manual.
- Uma coluna nova legítima gera um aviso do `schema_changes` uma vez; depois vira a nova referência.
- O Elementary não enxerga o `raw`: ali valem o balanço da carga e o monitor da fonte.

## O que o Elementary aberto cobre

Pela página de comparação do Elementary (consultada em 24/10/2026), a versão aberta traz os resultados dos testes do dbt, a linhagem entre tabelas, a cobertura de testes, os testes de anomalia como testes do dbt, o painel de qualidade e alertas básicos por Slack e Teams. A versão em nuvem acrescenta linhagem por coluna, gestão de incidentes, governança e vários projetos. As páginas Catalog, Data health, Environment, Alert rules e Pull requests do relatório aparecem desabilitadas; não consegui ler a documentação de cada uma, e tudo indica que são da nuvem (não confirmado). O projeto cobre a necessidade de cada uma por conta própria:

| Página desabilitada | O que cobre aqui |
| --- | --- |
| Catalog | `docs/03-consultar/01-catalogo.md`, gerado do dbt (`dado-publico catalog`) |
| Data health | `dado-publico observe` |
| Alert rules | alerta por e-mail do `observe` (o Elementary aberto só alerta por Slack e Teams) |
| Environment | não se aplica: há um ambiente |
| Pull requests | o próprio GitHub |

## Amostragem manual

A máquina não prova que o dado está certo. A cada fonte nova: comparar a contagem do raw com a das linhas dos arquivos, conferir alguns registros contra a página oficial e olhar quem foi filtrado.
