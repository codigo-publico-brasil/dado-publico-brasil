# Operar e publicar

Para quem opera a plataforma. Responde: como saber se algo quebrou, onde cada resultado é publicado, como rodar o pipeline por partes e o que fazer quando uma execução trava.

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
| Elementary (nos marts) | Volume que cai ou explode, coluna removida ou nova, nulos que aumentam; nos marts com data de evento (`fct_votacoes`, `fct_proposicoes`, `fct_normas`, `fct_emendas_convenios`), volume por dia com sazonalidade de dia da semana e frescor (a fonte parou de atualizar) | `metadata.dbt_results` e esquema `elementary` |
| Relatório e alerta | Junta tudo, falha se houver problema e envia por e-mail | `dado-publico observe` |
| Dagster | A saúde de cada fonte e da carga aparece como a verificação `saude_da_fonte` de cada tabela do raw (erro vira falha, aviso vira aviso); o sensor `falha_de_execucao` manda e-mail quando qualquer execução falha | interface do Dagster |

## Como usar

1. **Automático:** se uma execução falhar em qualquer passo, o sensor do Dagster manda e-mail com os passos que falharam e o link da execução (`DADO_PUBLICO_DAGSTER_URL`). E ao fim de cada fase de marts (`dado-publico transform` ou o Dagster), se houver problema, o relatório sai por e-mail. Configure no `.env` as variáveis `DADO_PUBLICO_SMTP_*` e `DADO_PUBLICO_ALERT_TO` (modelo em `.env.example`).
2. **Sob demanda:** `dado-publico observe` imprime o relatório (código 1 se houver problema); `dado-publico observe --email` também envia, útil para testar o SMTP.
3. **Relatório HTML do Elementary** (histórico dos testes, gráficos de anomalia), com o pipeline parado: `dado-publico observe --html` roda o `edr report` por `uvx` (precisa do [uv](https://docs.astral.sh/uv/)) e grava em `data_store/.state/observabilidade/report.html` (cerca de 13 MB). Com `--email`, o arquivo vai anexado. O alerta automático do fim da fase de marts não anexa o relatório, porque o `edr` precisa do warehouse livre. Ele **não é gerado sozinho** depois das execuções: gerar e servir o relatório a cada execução é a [issue 43](https://github.com/codigo-publico-brasil/dado-publico-brasil/issues/43). O `edr` escreve no warehouse, então rode com o Dagster parado.
4. **Erro:** investigar antes de publicar. **Aviso:** ler; muitas vezes é fato da fonte (por exemplo, arquivos antigos do Senado sem campos opcionais).

## Limites conhecidos

- Nos marts sem data de evento, a anomalia de volume só começa a valer depois de cerca de 7 execuções de histórico. Nos quatro com data, o histórico vem do próprio dado.
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
| Alert rules | alerta por e-mail do `observe` (o Elementary aberto só alerta por Slack e Teams) |
| Environment | não se aplica: há um ambiente |
| Pull requests | o próprio GitHub |

## Amostragem manual

A máquina não prova que o dado está certo. A cada fonte nova: comparar a contagem do raw com a das linhas dos arquivos, conferir alguns registros contra a página oficial e olhar quem foi filtrado.

## Onde cada resultado é publicado

| Resultado | Onde está hoje | Como acessar |
| --- | --- | --- |
| Esquema `marts` (as views `app_` viram tabelas) | PostgreSQL de serviço | `dado-publico publish` ([`01-rodar-localmente.md`](01-rodar-localmente.md)) |
| Catálogo e dicionário de colunas | Arquivo no repositório | [`03-consultar/01-catalogo.md`](../03-consultar/01-catalogo.md), gerado por `dado-publico catalog` |
| Site do dbt (linhagem, descrições, links das fontes) | **Só local** | `dado-publico docs`, em http://127.0.0.1:8080, com o pipeline parado |
| Relatório de observabilidade | Local ou e-mail | `dado-publico observe [--html] [--email]` |
| Fotos dos candidatos | Pasta de dados local (`fotos/<ano>/<UF>/<sq>.jpg`); a hospedagem pública depende da decisão do VPS (#30) | `uv run dado-publico fotos` extrai as imagens dos pacotes do TSE (já no landing), só o que falta ou mudou; o caminho está em `fct_candidaturas.foto_caminho` |

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

**Memória e temporários:** o dbt chega a 6,5 GB de memória na fase pós-identidade (issue 160), então o Docker Desktop precisa de pelo menos 8 GB. O compose monta um volume do Docker em `/data/warehouse.duckdb.tmp`: os arquivos temporários do DuckDB (spill) num bind mount do Windows falham ao ser relidos (`Cannot allocate memory`). Trocar o `temp_directory` pelo perfil do dbt não funciona: o DuckDB recusa mudar o diretório depois de usado. O DuckDB tem **teto de 5 GB** (`memory_limit`, no perfil do dbt e em toda conexão do projeto): o que passa disso vai para o disco, em vez de disputar a RAM com o sistema.

**Limites:** o Dagster só propaga a partir do que ele mesmo materializou, então na primeira vez rode `atualizar_tudo`. A interface **não tem login** no Dagster de código aberto: o serviço do `compose.yaml` escuta só em `127.0.0.1`; não o exponha à rede sem uma camada de autenticação na frente (ainda em aberto).

## Rodar por partes no container

O `dado-publico` roda igual dentro do container. Para um passo só, sem subir o agendador do Dagster (que lançaria execuções sozinho), pare o serviço e use um container avulso:

```bash
docker compose stop dagster
docker compose run --rm --no-deps -T dagster uv run --no-sync dado-publico transform
docker compose run --rm --no-deps -T dagster uv run --no-sync dado-publico publish
docker compose up -d --no-build dagster   # religa depois
```

No Git Bash do Windows, prefixe com `MSYS_NO_PATHCONV=1` quando um argumento tiver caminho. O `transform` mostra uma linha por modelo e por teste (`12 of 340 OK ...`) e marca as fases (`== transform_pre`, `== transform_post`); para acompanhar uma execução longa, mande a saída para um arquivo e use `tail -f`. Para refazer só um modelo e o que depende dele (por exemplo, depois de uma falha de memória no meio da fase 2):

```bash
docker compose run --rm --no-deps -T dagster uv run --no-sync python -c "
from dado_publico_brasil.core.settings import load_settings
from dado_publico_brasil.transformation import build
build.transform(load_settings(), 'transform_post', '--select', 'fct_candidaturas+', '--indirect-selection', 'cautious')"
```

Se o comando `dado-publico` do computador for bloqueado por política de aplicativo (erro "Controle de Aplicativo" no Windows), use `uv run python -m dado_publico_brasil.orchestration <comando>`.

### Recarregar uma captura ou um dataset

O arquivo e o hash no landing não mudam; só se marca a captura como não carregada e se carrega de novo:

1. `update metadata.captures set loaded_at = null where dataset = '<dataset>' and year = <ano>` (rode com `duckdb` ou `python` sobre o warehouse, com o pipeline parado).
2. `dado-publico load` (carrega só o que está pendente), depois `transform` e `publish`.

Dataset com chave natural (candidaturas) se atualiza por `merge`. Dataset com chave por hash tem uma armadilha (próxima seção).

## Armadilhas operacionais

Aprendidas na operação de 29 e 30/10/2026, com Docker Desktop no Windows:

- **Um container esquecido segura o warehouse.** O DuckDB aceita um escritor; um `dagster-run-*` ou o próprio `dagster` ainda ligado faz o próximo comando falhar com `Could not set lock on file ... Conflicting lock is held` ou `Permission denied`. Confira `docker ps -a`, pare o que sobrar e espere cerca de 20 segundos: o Docker libera a trava com atraso. Depois de matar um container, tente de novo antes de achar que o arquivo se corrompeu.
- **`Cannot allocate memory` ao ler ou escrever o warehouse não é falta de memória do DuckDB.** É o Windows com pouca RAM livre: o Docker acessa o arquivo por um compartilhamento do WSL. Feche programas pesados (navegadores, o aplicativo consumidor), libere o cache com `docker run --rm --privileged alpine sh -c "sync; echo 3 > /proc/sys/vm/drop_caches"` e refaça só o que falhou, como acima. O teto de 5 GB já está aplicado; o acompanhamento é a [issue 160](https://github.com/codigo-publico-brasil/dado-publico-brasil/issues/160).
- **O `publish` pode parar por uma consulta pesada no Postgres.** A troca do esquema (`DROP SCHEMA marts`) espera qualquer consulta que esteja lendo `marts`. Se ele não termina, olhe `select pid, state, wait_event_type, now() - query_start from pg_stat_activity where state <> 'idle'`: uma sessão em `Lock` e outra `active` há muito tempo; encerre a segunda com `select pg_terminate_backend(<pid>)`. Cancelar o comando no cliente não encerra a consulta no servidor.
- **Coluna nova em dataset com `primary_key: [_row_hash]` duplica o raw.** Votação e prestação de contas usam o hash da linha inteira como chave; acrescentar uma coluna ao contrato muda o hash de toda linha, e recarregar a captura **insere as linhas novas sem remover as antigas** (os votos contariam em dobro). Depois de recarregar, compare `count(*)` com `count(<coluna nova>)`, confirme que cada linha sem a coluna tem uma gêmea com ela e apague as antigas. Recarregue só o ano necessário. Acompanhamento: [issue 156](https://github.com/codigo-publico-brasil/dado-publico-brasil/issues/156).
- **Consulta de conferência esquecida.** `Ctrl+C` no cliente não para a consulta no servidor; sempre use `timeout` e confira `pg_stat_activity` depois.

## Reconstruir o warehouse do zero, a partir do landing

Quando o warehouse precisa ser refeito (mudança incompatível, arquivo corrompido, limpeza geral). O raw, o dbt e as consultas se refazem do landing; a **identidade é criada de novo, com chaves `id_pessoa` novas** (a cópia da anterior fica em `snapshots/identity`), então só faça isso se nenhuma aplicação guarda as chaves antigas. O que **não** se refaz do landing é o registro das capturas (URL, data, hash, ETag e itens de cada lote), que mora em `metadata` (issue 153): por isso o comando leva o `metadata` do warehouse antigo e descarta o resto.

1. **Pare tudo que escreve no warehouse**, em especial o Dagster (`docker stop dado-publico-brasil-dagster-1`): uma imagem com código antigo apagaria as ligações novas da identidade.
2. Mova o warehouse antigo para fora do caminho, **sem apagá-lo** (ele é a fonte do `metadata`):

```bash
mkdir data_store/backup
mv data_store/warehouse.duckdb data_store/backup/
```

3. Rode a reconstrução (cria o warehouse, leva o `metadata`, guarda o estado antigo do dlt como `.state/dlt.antes-<data>`, recarrega o raw do landing com `load --rebuild`, roda o dbt, cria a identidade e roda o dbt de novo). **Leva cerca de seis horas**: o raw tem uns 70 milhões de linhas e quase todo o tempo vai na votação do TSE (55 milhões), que o dlt grava em `INSERT ... VALUES` (issue 154). A parte do dbt e da identidade leva cerca de vinte minutos:

```bash
uv run dado-publico rebuild --old-warehouse data_store/backup/warehouse.duckdb
```

Se parar no meio, `uv run dado-publico load --rebuild` e `uv run dado-publico transform` retomam as duas metades.

4. **Confira** antes de religar o Dagster e de apagar o backup:

| Conferência | Como |
| --- | --- |
| Todas as capturas carregaram | `uv run dado-publico query --sql "select count(*), count(loaded_at) from metadata.captures"` (as duas contagens iguais) |
| O raw tem as mesmas linhas do antigo | compare `select count(*)` de cada tabela `raw_*` com o warehouse antigo (abra o antigo somente leitura com `duckdb`) |
| O landing está íntegro e a identidade tem cópia | `uv run dado-publico verify` |
| Nenhum teste do dbt reprova | `uv run dado-publico observe` (0 reprovados; a seção "Saúde por dimensão" mostra o resto) |
| Os modelos novos têm o tamanho esperado | `select count(*)` em `dim_pessoas`, `fct_mandatos`, `fct_eventos`, `agg_composicoes`, `fct_votos` e `app_*` contra o warehouse antigo |
| A identidade está sã | `dim_pessoas` e `identity.pessoa` com o mesmo número; nenhum mandato sem `id_pessoa` |
| O raw bate com o antigo | As diferenças esperadas são só de versões: o `load --rebuild` carrega a **versão mais recente** de cada arquivo, e a carga diária **soma** as versões nos datasets `merge` (issue 155). Fora disso, as contagens devem ser iguais; uma diferença de dobro é duplicação no antigo (foi o caso da votação de 2022) |
| Reconstruiu igual | rode `transform` de novo: nenhuma pessoa nova, nenhum snapshot novo |

5. Reconstrua a imagem do Dagster com o código atual (`docker compose --profile pipeline up -d --build`) antes de religá-lo.

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
