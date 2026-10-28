# Operar e publicar

Para quem opera a plataforma. Cobre a observabilidade dos dados e onde cada resultado é publicado.

## Observabilidade dos dados

Para quem opera a plataforma: como saber, a cada atualização, se algo quebrou na origem, na carga ou na lógica, sem olhar tabela por tabela. Decisão em [ADR 0018](../05-decisoes/0018-observabilidade-dos-dados.md).

### Camadas

| Camada | O que pega | Onde fica |
| --- | --- | --- |
| Monitor da fonte | Fonte fora do ar, coluna que sumiu ou apareceu (`schema`, `schema_mudou`), queda de volume | `metadata.source_checks` |
| Integridade do download | Antes de virar captura, o arquivo não pode ser uma página HTML no lugar do esperado, o tamanho tem de bater com o `Content-Length` informado e, nos `.zip`, o pacote abre sem erro e tem o membro esperado (`member`, como `*.xml` no DOU). Reprovado vira `integridade` com erro, o arquivo fica no landing como evidência, não vira captura e a próxima execução tenta de novo | `metadata.source_checks` |
| Partições que faltam | Por dataset anual, mensal ou por legislatura, as partições esperadas contra as capturadas (`particoes`). A execução incremental recupera sozinha as que faltam (as mais recentes primeiro, até 3 por dataset e por execução); a que a fonte não publica (404) vira "indisponível" e não é tentada de novo. `dado-publico coverage` lista as lacunas | `metadata.source_checks` |
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
- **TLS no `publish`:** o `publish` recusa um DSN de servidor que não seja local (`localhost`, `127.0.0.1`, `::1` ou o serviço `postgres` do compose) e não exija `sslmode=require`, `verify-ca` ou `verify-full`; a senha e os dados do serviço não trafegam sem criptografia. O papel de leitura por aplicação depende do Postgres de produção (#30).
- **Saúde por dimensão:** `dado-publico observe` mostra uma nota por dimensão de qualidade (frescor, completude, acurácia, consistência, unicidade e validade) e uma geral, calculadas dos testes do último build: passou vale 100, avisou 50 e falhou 0, e a nota da dimensão é a média. Cada teste cai na dimensão pelo nome (`not_null` é completude; `unique`, unicidade; `relationships`, consistência; `accepted_values`, validade; os do Elementary pelo tipo) ou pela pasta (`gaps` é completude; `reconciliation`, consistência); a regra fica em `transformation/health.py`, e um teste reprova se algum teste novo ficar sem dimensão. Os testes de lacuna são avisos permanentes e puxam a completude para baixo de forma estável: a lista do que puxa vem junto com a nota, e a leitura é "estas lacunas conhecidas", não degradação. É nota de saúde dos **dados**, nunca de pessoas.
- **Captura velha:** o dataset que declara `max_age_days` no contrato e não foi verificado nesse prazo aparece em `observe` e no e-mail como problema (a pipeline parou ou a fonte deixou de responder); um dataset com limite e nenhuma captura também.
- Recesso do Congresso (julho e dezembro a janeiro) pode gerar aviso de volume e de frescor: é esperado, e o aviso é só informação.
- `load --rebuild` descarta a tabela raw do dataset (e as tabelas filhas) e o estado do dlt antes de recarregar do landing; por isso mudar a chave primária de um contrato não exige apagar nada à mão.
- O `merge` do dlt não apaga: uma linha que a fonte removeu continua no raw. O aviso `linhas_removidas` conta as que vieram de capturas anteriores do mesmo arquivo e a atual não traz; decidir o que fazer com elas é manual.
- Uma coluna nova legítima gera um aviso do `schema_changes` uma vez; depois vira a nova referência.
- O Elementary não enxerga o `raw`: ali valem o balanço da carga e o monitor da fonte.

## O que o Elementary aberto cobre

Pela página de comparação do Elementary (consultada em 24/10/2026), a versão aberta traz os resultados dos testes do dbt, a linhagem entre tabelas, a cobertura de testes, os testes de anomalia como testes do dbt, o painel de qualidade e alertas básicos por Slack e Teams. A versão em nuvem acrescenta linhagem por coluna, gestão de incidentes, governança e vários projetos. As páginas Catalog, Data health, Environment, Alert rules e Pull requests do relatório aparecem desabilitadas; não consegui ler a documentação de cada uma, e tudo indica que são da nuvem (não confirmado). O projeto cobre a necessidade de cada uma por conta própria:

| Página desabilitada | O que cobre aqui |
| --- | --- |
| Catalog | `docs/03-consultar/01-catalogo.md`, gerado do dbt (`dado-publico catalog`) |
| Data health | `dado-publico observe` |
| Fotos dos candidatos | `uv run dado-publico fotos` extrai as imagens dos pacotes do TSE (já no landing) para `<pasta de dados>/fotos/<ano>/<UF>/<sq>.jpg`, só o que falta ou mudou; o caminho está em `fatos.candidaturas.foto_caminho`. Hospedagem pública das fotos depende da decisão do VPS (#30) |
| Alert rules | alerta por e-mail do `observe` (o Elementary aberto só alerta por Slack e Teams) |
| Environment | não se aplica: há um ambiente |
| Pull requests | o próprio GitHub |

## Amostragem manual

A máquina não prova que o dado está certo. A cada fonte nova: comparar a contagem do raw com a das linhas dos arquivos, conferir alguns registros contra a página oficial e olhar quem foi filtrado.

## Onde cada resultado é publicado

| Resultado | Onde está hoje | Como acessar |
| --- | --- | --- |
| Marts e esquema `servico` (as views viram tabelas) | PostgreSQL de serviço | `dado-publico publish` ([`01-rodar-localmente.md`](01-rodar-localmente.md)) |
| Catálogo e dicionário de colunas | Arquivo no repositório | [`03-consultar/01-catalogo.md`](../03-consultar/01-catalogo.md), gerado por `dado-publico catalog` |
| Site do dbt (linhagem, descrições, links das fontes) | **Só local** | `dado-publico docs`, em http://127.0.0.1:8080, com o pipeline parado |
| Relatório de observabilidade | Local ou e-mail | `dado-publico observe [--html] [--email]` |

O site do dbt ainda não é publicado na internet. O caminho usual é `dbt docs generate --static` (gera um único HTML) numa etapa do CI e hospedagem em página estática (por exemplo GitHub Pages); a decisão está em aberto numa issue.

## Dagster: o pipeline sozinho

O Dagster ([ADR 0027](../05-decisoes/0027-orquestracao-automatica-por-fonte.md)) liga tudo, sem você apertar nada:

| O que | Como |
| --- | --- |
| **Captura agendada** | cada fonte com `schedule` no YAML tem um agendamento `captura_<fonte>` (landing e raw). Mudar a cadência é mudar o cron no YAML |
| **Propagação** | quando o raw de uma fonte recebe dado novo, o dbt, a identidade e a publicação no PostgreSQL rodam sozinhos (`AutomationCondition.eager`). Sem dado novo, nada a jusante roda |
| **Atraso** | cada fonte agendada tem uma verificação de frescor: sem captura por mais de 1,5 intervalo do cron, o ativo `landing/<fonte>` aparece como atrasado |
| **Uma execução por vez** | `dagster.yaml` limita a fila a uma execução (o DuckDB aceita um escritor) |

**Jobs** (na interface, aba *Jobs*, *Launch run*): `atualizar_<fonte>` refaz tudo o que vem da fonte (por exemplo, `atualizar_tse`: captura, raw, dbt, identidade, publicação); `captura_<fonte>` só captura; `atualizar_tudo` refaz tudo; `capturar_tudo` captura todas as fontes sem processar; `processar_tudo` roda dbt, identidade e publicação com o que já está no raw, sem capturar nada. Para um ano ou modo diferente, abra o *launchpad* do job e ajuste `mode` (`incremental`, `historical`, `years`).

**Ver o que está atrasado e executar:** na interface, *Assets* mostra a última atualização de cada ativo e os atrasos (verificação *freshness*); selecione os ativos parados e use *Materialize* (com *downstream*, se quiser propagar). Os sensores `propagar_atualizacoes` e `verificar_atrasos` e os agendamentos sobem ligados.

**Limites:** o Dagster só propaga a partir do que ele mesmo materializou, então na primeira vez rode `atualizar_tudo`. A interface **não tem login** no Dagster de código aberto: o serviço do `compose.yaml` escuta só em `127.0.0.1`; não o exponha à rede sem uma camada de autenticação na frente (ainda em aberto).

## Como saber o que está desatualizado

Dois tempos diferentes, os dois em `metadata.captures`: `captured_at` (quando **chegou conteúdo novo** da fonte) e `last_checked_at` (quando o pipeline **perguntou** à fonte pela última vez). Dataset com `last_checked_at` antigo está sem rodar; com `captured_at` antigo mas verificação recente, a fonte é que não publicou nada.

```bash
uv run dado-publico query --sql "SELECT source, dataset, max(captured_at) AS ultimo_dado_novo, max(last_checked_at) AS ultima_verificacao FROM metadata.captures GROUP BY 1, 2 ORDER BY 4"
```

Outras visões:

- **Dagster:** *Assets* mostra a última atualização de cada ativo e o atraso da captura (veja acima); a verificação `saude_da_fonte` mostra o último monitor da fonte (fora do ar, coluna que mudou, queda de volume).
- `dado-publico observe`: resumo da saúde das fontes, da carga e dos testes (falha se houver problema).
- **Frescor do dbt:** cada fonte declara `freshness` (`warn_after`, `error_after`) e o `dbt source freshness` roda no `transform`, gravando em `metadata.dbt_results`. Ele mede a idade da **última carga nossa**, não se a origem publicou algo novo.

**O que ainda não existe:** um comando que pergunte às origens "há dado novo?" sem baixar. Hoje a pergunta é feita dentro da captura agendada (o pedido leve de `ETag`/`Last-Modified` antes de baixar), que roda no `schedule` de cada fonte. O alerta de atraso aparece na interface; o aviso por e-mail só cobre execuções que falham.
