# Operar e publicar

Para quem opera a plataforma. Responde: como saber se algo quebrou, onde cada resultado é publicado, como rodar o pipeline por partes e o que fazer quando uma execução trava.

## Observabilidade dos dados

Para quem opera a plataforma: como saber, a cada atualização, se algo quebrou na origem, na carga ou na lógica, sem olhar tabela por tabela. Decisão em [ADR 0018](../05-decisoes/0018-observabilidade-dos-dados.md).

### Camadas

| Camada | O que pega | Onde fica |
| --- | --- | --- |
| Monitor da fonte | Fonte fora do ar, coluna que sumiu ou apareceu (`schema`, `schema_mudou`), queda de volume | `metadata.fontes_verificacoes` |
| Integridade do download | Antes de virar captura, o arquivo não pode ser uma página HTML no lugar do esperado, o tamanho tem de bater com o `Content-Length` informado e, nos `.zip`, o pacote abre sem erro e tem o membro esperado (`member`, como `*.xml` no DOU). Reprovado vira `integridade` com erro, o arquivo fica no landing como evidência, não vira captura e a próxima execução tenta de novo | `metadata.fontes_verificacoes` |
| Partições que faltam | Por dataset anual, mensal ou por legislatura, as partições esperadas contra as capturadas (`particoes`). A execução incremental recupera sozinha as que faltam (as mais recentes primeiro, até 3 por dataset e por execução); a que a fonte não publica (404) vira "indisponível" e não é tentada de novo. Dataset `on_demand` (fotos do TSE) fica fora do incremental e da recuperação e não gera aviso de lacuna: só se captura pedindo (`--years`, `--historical`, `--dataset`). `dado-publico coverage` lista as lacunas | `metadata.fontes_verificacoes` |
| Balanço da carga | Linhas lidas, filtradas, carregadas, rejeitadas e colisões de chave (`carga`); linhas de capturas anteriores que a atual não traz (`linhas_removidas`) | `metadata.fontes_verificacoes` |
| Testes do dbt | Regras de negócio, conciliação entre camadas (`reconciliation`), lacunas conhecidas (`gaps`) | `metadata.testes_resultados` (com `qtd_segundos`, o tempo de cada nó) |
| Elementary (nos marts) | Volume que cai ou explode, coluna removida ou nova, nulos que aumentam; nos marts com data de evento (`fct_votacoes`, `fct_proposicoes`, `fct_normas`, `fct_emendas_convenios`), volume por dia com sazonalidade de dia da semana e frescor (a fonte parou de atualizar) | `metadata.testes_resultados` e esquema `elementary` |
| Relatório e alerta | Junta tudo, falha se houver problema e envia por e-mail | `dado-publico observe` |
| Dagster | A saúde de cada fonte e da carga aparece como a verificação `saude_da_fonte` de cada tabela do raw (erro vira falha, aviso vira aviso). A execução segue em SUCCESS mesmo com a verificação em erro (nada é bloqueado): quem avisa é o sensor `verificacoes_em_erro` (abaixo). O sensor `falha_de_execucao` manda e-mail quando uma execução falha | interface do Dagster |

## Como usar

1. **Automático:** o sensor `verificacoes_em_erro` olha, a cada 5 minutos, as avaliações novas de verificação de ativo (evento `ASSET_CHECK_EVALUATION`, lido do registro de eventos da instância, sem abrir o warehouse) e avisa das reprovadas com severidade ERROR, um aviso por tique com todos os ativos (o cursor é o instante da última avaliação lida, então nada se repete; na primeira vez olha as últimas 24 h). Sem SMTP configurado, o aviso fica no log do tique (nível erro) e na mensagem do tique, visíveis em *Automation > verificacoes_em_erro* na interface. Verificação com severidade WARN (e teste do dbt em aviso) não dispara aviso: aparece em *Assets* e no `observe`. Se uma execução falhar em qualquer passo, o sensor do Dagster manda e-mail com os passos que falharam e o link da execução (`DADO_PUBLICO_DAGSTER_URL`). E ao fim de cada fase de marts (`dado-publico transform` ou o Dagster), se houver problema, o relatório sai por e-mail. Configure no `.env` as variáveis `DADO_PUBLICO_SMTP_*` e `DADO_PUBLICO_ALERT_TO` (modelo em `.env.example`).
2. **Sob demanda:** `dado-publico observe` imprime o relatório (código 1 se houver problema); `dado-publico observe --email` também envia, útil para testar o SMTP.
3. **Relatório HTML do Elementary** (histórico dos testes, gráficos de anomalia), com o pipeline parado: `dado-publico observe --html` roda o `edr report` por `uvx` (precisa do [uv](https://docs.astral.sh/uv/)) e grava em `data_store/.state/observabilidade/report.html` (cerca de 13 MB). Com `--email`, o arquivo vai anexado. O alerta automático do fim da fase de marts não anexa o relatório, porque o `edr` precisa do warehouse livre. Ele **não é gerado sozinho** depois das execuções: gerar e servir o relatório a cada execução é a [issue 43](https://github.com/codigo-publico-brasil/dado-publico-brasil/issues/43). O `edr` escreve no warehouse, então rode com o Dagster parado.
4. **Erro:** investigar antes de publicar. **Aviso:** ler; muitas vezes é fato da fonte (por exemplo, arquivos antigos do Senado sem campos opcionais).

## Limites conhecidos

- Nos marts sem data de evento, a anomalia de volume só começa a valer depois de cerca de 7 execuções de histórico. Nos quatro com data, o histórico vem do próprio dado.
- **Saúde por dimensão:** `dado-publico observe` mostra uma nota por dimensão de qualidade (frescor, completude, acurácia, consistência, unicidade e validade) e uma geral, calculadas dos testes do último build: passou vale 100, avisou 50 e falhou 0, e a nota da dimensão é a média. Cada teste cai na dimensão pelo nome (`not_null` é completude; `unique`, unicidade; `relationships`, consistência; `accepted_values`, validade; os do Elementary pelo tipo) ou pela pasta (`gaps` é completude; `reconciliation`, consistência); a regra fica em `transformation/health.py`, e um teste reprova se algum teste novo ficar sem dimensão. Os testes de lacuna são avisos permanentes e puxam a completude para baixo de forma estável: a lista do que puxa vem junto com a nota, e a leitura é "estas lacunas conhecidas", não degradação. É nota de saúde dos **dados**, nunca de pessoas.
- **Captura velha:** o dataset que declara `max_age_days` no contrato e não foi verificado nesse prazo aparece em `observe` e no e-mail como problema (a pipeline parou ou a fonte deixou de responder); um dataset com limite e nenhuma captura também.
- Recesso do Congresso (julho e dezembro a janeiro) pode gerar aviso de volume e de frescor: é esperado, e o aviso é só informação.
- `load --rebuild` descarta a tabela raw do dataset (e as tabelas filhas) e o estado do dlt antes de recarregar do landing; por isso mudar a chave primária de um contrato não exige apagar nada à mão.
- O `merge` do dlt não apaga: uma linha que a fonte removeu continua no raw (nos datasets `replace_partition` ela sai com a versão antiga e o aviso não existe). O aviso `linhas_removidas` conta as que vieram de capturas anteriores do mesmo arquivo e a atual não traz; decidir o que fazer com elas é manual.
- **Tempo da carga do raw** (ADR 0043, medido numa máquina de desenvolvimento, não no servidor): votação do TSE de 2016 (943 mil linhas) em 160 s com Parquet contra 1.062 s com `insert_values`; a de 2026 (6,7 milhões de linhas, zip de 446 MB) em 28 min com `merge` e 19 min com `replace_partition`, pico de 2,9 GB e 1,5 GB. Mais da metade é a leitura do CSV em Python. Acompanhe a carga na aba *Runs*: o ativo `raw_<fonte>` avisa o dataset, o arquivo, o tamanho e as linhas lidas a cada 30 s.
- **Carga que leu 0 linhas** de um arquivo que já teve linhas (`volume` de N para 0) é erro: a captura foi marcada como carregada sem entrar no raw, que fica com a versão anterior. Corrija com `load --rebuild --dataset <nome>` (reconstrói do landing).
- **`optional` no contrato** (colunas que a fonte omite quando vazias, como número e data de normas e vetos antigos do Senado) evita o aviso `schema` por partição; o aviso já gravado só some quando o arquivo é conferido de novo (`dado-publico recheck`).
- Uma coluna nova legítima gera um aviso do `schema_changes` uma vez; depois vira a nova referência.
- O Elementary não enxerga o `raw`: ali valem o balanço da carga e o monitor da fonte.

## O que o Elementary aberto cobre

Pela página de comparação do Elementary (consultada em 24/10/2026), a versão aberta traz os resultados dos testes do dbt, a linhagem entre tabelas, a cobertura de testes, os testes de anomalia como testes do dbt, o painel de qualidade e alertas básicos por Slack e Teams. A versão em nuvem acrescenta linhagem por coluna, gestão de incidentes, governança e vários projetos. As páginas Catalog, Data health, Environment, Alert rules e Pull requests do relatório aparecem desabilitadas; não consegui ler a documentação de cada uma, e tudo indica que são da nuvem (não confirmado). O projeto cobre a necessidade de cada uma por conta própria:

| Página desabilitada | O que cobre aqui |
| --- | --- |
| Catalog | `docs/03-consultar/01-catalogo.md`, gerado do dbt (`dado-publico catalog`) |
| Data health | `dado-publico observe` |
| Arquivos servidos (DOU, fotos) | a carga materializa, em `<pasta de dados>/arquivos/<poder>/<esfera>/<fonte>/arq_<coleção>/`, o que o bloco `arquivos` do dataset declara (cópia ou extração do pacote do landing, só o que falta ou mudou); o `export` publica o que tem `publicar: true`. `fct_candidaturas.foto_caminho` é o caminho no lake. Veja [especificação de fonte](03-especificacao-de-fonte.md) e [ADR 0037](../05-decisoes/0037-arquivos-no-lake-com-prefixo-arq.md) |
| Alert rules | alerta por e-mail do `observe` (o Elementary aberto só alerta por Slack e Teams) |
| Environment | não se aplica: há um ambiente |
| Pull requests | o próprio GitHub |

## Amostragem manual

A máquina não prova que o dado está certo. A cada fonte nova: comparar a contagem do raw com a das linhas dos arquivos, conferir alguns registros contra a página oficial e olhar quem foi filtrado.

## Onde cada resultado é publicado

| Resultado | Onde está hoje | Como acessar |
| --- | --- | --- |
| `staging`, `intermediate`, `marts` e `metadata.capturas` em Parquet, com `catalogo.duckdb` e `manifesto.json` | Lake público no R2 (`datalake.codigopublicobrasil.com.br`) | `dado-publico export` (só depois dos testes do dbt; sobe apenas o que mudou, por hash); consumo em [`06-consumir-o-lake.md`](../03-consultar/06-consumir-o-lake.md) ([ADR 0035](../05-decisoes/0035-lakehouse-publico-no-r2.md)) |
| Cópias da identidade e `metadata` (ADR 0036) | Bucket privado do R2 (**nunca público**: sem domínio nem `r2.dev`) | `DADO_PUBLICO_R2_BUCKET_PRIVADO`, só na máquina de produção; sem a variável, tudo local |
| Landing e `arquivos/` local | **Só no disco local** (risco aceito, ADR 0036); o que é publicável também está no lake público (`arq_`) | nenhuma cópia; veja "Restaurar numa máquina vazia" |
| Catálogo e dicionário de colunas | Arquivo no repositório | [`03-consultar/01-catalogo.md`](../03-consultar/01-catalogo.md), gerado por `dado-publico catalog` |
| Site do dbt (linhagem, descrições, links das fontes) | **Só local** | `dado-publico docs`, em http://127.0.0.1:8080, com o pipeline parado |
| Relatório de observabilidade | Local ou e-mail | `dado-publico observe [--html] [--email]` |

O `export` **recusa** (nada é apagado nem publicado) se faltar no warehouse alguma tabela do manifesto publicado: protege o lake de um warehouse errado ou incompleto. Para retirar de propósito uma tabela que deixou de existir, rode `dado-publico export --prune`.

**Destino:** o CLI lê o `.env` da pasta onde roda (ou o arquivo de `DADO_PUBLICO_ENV_FILE`) sem sobrescrever o que o shell já define. Com as quatro `DADO_PUBLICO_R2_*` o `export` grava no bucket; sem elas grava em `<pasta de dados>/lake`. Confira o destino antes de dizer que publicou: pasta local não é o lake público (o `manifesto.json` público é a prova).

O `export` imprime uma linha por tabela (`ignorada` ou `gravada`, com os segundos) e o tempo de cada fase; os tempos por tabela ficam também em `<pasta de dados>/.state/export_tempos.json` (só a última rodada). Em rodada sem mudança só lê (impressões digitais, quatro tabelas por vez): não grava, não envia e não troca `catalogo.duckdb` nem `manifesto.json`. Os objetos órfãos só são procurados sob as tabelas gravadas; `--prune` varre todas (e as coleções `arq_`: objeto que saiu do controle só é apagado com `--prune`). Sem mudança, `id_execucao`, `dt_exportacao` e `versao_commit` do manifesto e do catálogo continuam os da última rodada que mudou algo; mudar a URL base (`DADO_PUBLICO_LAKE_URL`) conta como mudança. Resto de rodada interrompida (objeto gravado antes do manifesto) não deixa estado para trás que a rodada seguinte enxergue se a tabela voltar a ser ignorada; `--prune` limpa.

**Memória:** o `export` usa `preserve_insertion_order = false` (a ordem só vale onde há `ORDER BY`) e, depois das tabelas, fecha o warehouse e abre uma instância nova do DuckDB para a fase de arquivos, que não precisa dele; assim a memória das varreduras e dos COPY das tabelas não sobra para os arquivos.

**Retomada:** o `export` é retomável. Catálogo e manifesto são trocados ao fim das tabelas e de novo depois de cada coleção de arquivos concluída (sempre depois dos arquivos e do controle), então uma queda na fase de arquivos não perde as tabelas. Antes de enviar uma coleção com pendentes, lista o destino (ListObjectsV2 no R2) e não reenvia arquivo novo cuja chave já existe com o mesmo tamanho (o PUT leva o SHA-256 e o R2 recusa corpo que não confere). Arquivo que mudou é sempre reenviado (o tamanho não prova o conteúdo). Limitações: uma tabela gravada e não registrada (queda durante a fase de tabelas) é regravada, porque o Parquet leva metadados da execução e não tem SHA previsível; uma coleção interrompida deixa objetos fora do controle até a rodada seguinte (o `verify` os aponta).

O comando `dado-publico publish-docs` (o `run` o chama sozinho depois do `export`) sobe ao R2, como arquivos únicos, o site do dbt (`docs/dbt.html`), o relatório do Elementary (`docs/qualidade.html`) e a página inicial do lake (`docs/index.html`, a partir de `site/index.html`, no estilo do site da organização, com a ficha preenchida pelo `manifesto.json`). O warehouse precisa estar livre; sem as variáveis do R2, nada é publicado. Esses arquivos ficam fora dos prefixos das tabelas, então o `export` não os apaga. O Elementary não grava amostras de linhas de testes (`test_sample_row_count: 0`), porque o relatório é público. Nenhuma das duas ferramentas aceita tema próprio, então o HTML gerado é ajustado em `transformation/branding.py` (título, ícone da aba e atalho de volta à página inicial; o logo de cada ferramenta continua na interface), `prune_static` (sem pacotes nem exposures no site do dbt) e `prune_report` (sem as páginas do Elementary Cloud e com política de segurança que bloqueia terceiros). O relatório sai sem rastreamento (`dbt/edr/config.yml`), sem amostras de dados e com o nome do projeto. A apresentação do site do dbt é o bloco `__overview__` de `dbt/models/overview.md`. Se uma versão nova de uma ferramenta mudar o formato, o `publish-docs` falha com erro claro.

**Uma vez, no painel da Cloudflare** (o R2 não serve `index.html` sozinho): em *Rules → Transform Rules → Rewrite URL*, regra para `datalake.codigopublicobrasil.com.br` com `URI Path` igual a `/` que reescreve o caminho (estático) para `/docs/index.html`.

## Dagster: o pipeline sozinho

O Dagster ([ADR 0027](../05-decisoes/0027-orquestracao-automatica-por-fonte.md)) liga tudo, sem você apertar nada:

| O que | Como |
| --- | --- |
| **Captura noturna** | cada fonte com `schedule` no YAML tem um agendamento `captura_<fonte>` (landing e raw), escalonado de madrugada. Mudar a cadência é mudar o cron no YAML |
| **Ciclo a jusante** | `processar_e_publicar`, às 04:00, roda o job `processar_tudo`: dbt, identidade e dbt pós-identidade; ao terminar com sucesso, o sensor `publicar_apos_processar` pede o job `publicar` (export do lake e docs), o último passo ([ADR 0046](../05-decisoes/0046-publicacao-tolerante-a-falhas-de-nos-isolados.md)). Só roda se o raw recebeu dado desde o último ciclo completo (consulta o log do Dagster, sem abrir o warehouse). Não há disparo por evento ([ADR 0042](../05-decisoes/0042-ciclo-noturno-de-processamento-e-publicacao.md)) |
| **No máximo uma vez por dia** | cada agendamento pula se o job já teve execução com sucesso (ou em andamento) desde 00:00 de São Paulo. **Execução que falhou não conta**: pode ser relançada à mão ou pelo tique do dia seguinte; não há `run_retries` (`dagster.yaml`) e os sensores de falha só avisam |
| **Atraso** | cada fonte agendada tem uma verificação de frescor: sem captura por mais de 1,5 intervalo do cron, o ativo `landing/<fonte>` aparece como atrasado |
| **Uma execução por vez** | `dagster.yaml` limita a fila a uma execução (o DuckDB aceita um escritor) |

**Horários (America/Sao_Paulo):**

| Agendamento | Quando | Observação |
| --- | --- | --- |
| `captura_camara` | 01:00, todo dia | |
| `captura_senado` | 01:20 | |
| `captura_transparencia` | 01:40 | |
| `captura_constituicao` | 01:50 | |
| `captura_dou` | 02:00 | |
| `captura_ibge` | 02:10, dia 1 | mensal |
| `captura_tse` | sem agendamento | desativado após as eleições; só manual (`captura_tse`, `atualizar_tse`). Para reativar, volte o cron ao YAML. O TSE segue no ciclo a jusante com o que há no raw |
| `processar_e_publicar` | 04:00 (`pipeline.CYCLE_CRON`) | depois da última captura, com folga; se uma captura passar das 04:00 o ciclo espera na fila (FIFO, uma execução por vez) |

Uma captura que falha não impede o ciclo: ele roda com o que há no raw, e o atraso aparece na verificação de frescor e no aviso da execução que falhou. A publicação (`publicacao/lake`, `publicacao/docs`) só sai do job `publicar`, pedido pelo sensor depois de um job que processa, ou à mão.

**Jobs** (na interface, aba *Jobs*, *Launch run*): `atualizar_<fonte>` refaz tudo o que vem da fonte (por exemplo, `atualizar_tse`: captura, raw, dbt, identidade, publicação); `captura_<fonte>` só captura; `atualizar_tudo` refaz tudo; `capturar_tudo` captura todas as fontes sem processar; `processar_tudo` roda dbt e identidade com o que já está no raw, sem capturar nada (a publicação vem em seguida, pelo sensor); `publicar` só publica (o lake no R2 e as docs) o que já está pronto no warehouse, sem capturar nem transformar, para rodar quando você quiser. Para um ano ou modo diferente, abra o *launchpad* do job e ajuste `mode` (`incremental`, `historical`, `years`).

**Por que o dbt roda em duas fases, com a identidade no meio.** A identidade (`identity.pessoas`) é código Python e precisa de modelos do dbt que a precedem (`int_pessoas_ids_vistos`, a lista de identificadores vistos nas fontes); os modelos seguintes (`dim_pessoas`, mandatos, votos...) precisam de `identity.pessoas` já pronta. Um único `dbt build` não expressa isso, então o dbt é dividido por tag (`pre_identity`, em `dbt_project.yml`; ver [Camadas](../01-entender/03-camadas.md)). No job `processar_tudo` as operações saem nesta ordem (e um teste confere; a publicação é uma execução à parte porque o Dagster pula o passo cujo insumo não foi materializado):

```text
dbt_pre_identity -> identity -> dbt_post_identity      (depois, em outra execução: publicacao/lake -> publicacao/docs)
(modelos tag:pre_identity)  (identity.pessoas, ..._identificadores, ..._fusoes)  (os demais modelos)  (export Parquet, docs)
```

A linhagem por modelo na interface do Dagster mostra modelos e ativos, não essas fases: as fases são as **operações** do job (aba *Runs*, cada passo leva o nome acima). A ligação é pelo grafo: `identity/*` depende de `intermediate/int_pessoas_ids_vistos` e os modelos que leem `source('identity', ...)` dependem de `identity/*`. Uma chave de ativo errada vira um ativo-stub sem op e quebra a ordem em silêncio; o teste `tests/orchestration/test_graph.py` falha se um ativo executável depender de stub. O único stub que resta é `metadata/capturas` (tabela gravada por todas as fontes, sem ativo próprio). As tabelas aninhadas do dlt (`dataset__filho`, gravadas junto com o dataset) apontam ao ativo de raw do dataset pelo tradutor do dbt em `definitions.py`.

**Ver o que está atrasado e executar:** na interface, *Assets* mostra a última atualização de cada ativo e os atrasos (verificação de atraso da captura); selecione os ativos parados e use *Materialize* (com *downstream*, se quiser propagar). O sensor `verificar_atrasos`, o de falha de execução e os agendamentos sobem ligados.

**Memória e temporários:** o dbt chega a 6,5 GB de memória na fase pós-identidade (issue 160), então o Docker Desktop precisa de pelo menos 8 GB. O compose monta `/data/warehouse.duckdb.tmp` sob a pasta de dados (Linux); no Windows os arquivos temporários do DuckDB (spill) num bind mount falham ao ser relidos (`Cannot allocate memory`): defina `DADO_PUBLICO_SPILL=duckdb_tmp` no `.env` para usar um volume do Docker. Trocar o `temp_directory` pelo perfil do dbt não funciona: o DuckDB recusa mudar o diretório depois de usado. O DuckDB tem **teto de 5 GB** (`memory_limit`, no perfil do dbt e em toda conexão do projeto): o que passa disso vai para o disco, em vez de disputar a RAM com o sistema.

**Limites:** o ciclo noturno só roda se o raw registrou atualização no Dagster; na primeira vez rode `atualizar_tudo` (num servidor, `scripts/servidor.sh primeira-carga`). A interface **não tem login** no Dagster de código aberto: o `webserver` do `compose.yaml` escuta só em `127.0.0.1`; não o exponha à rede sem uma camada de autenticação na frente (ainda em aberto).

## Implantar num servidor

Para quem vai deixar o pipeline rodando sozinho num servidor (uma máquina local ou um VPS). **Você não entra no servidor para atualizar**: o CI constrói a imagem e a publica no GHCR quando o código entra na `main` (`.github/workflows/imagem.yml`, com o `sha` do commit como etiqueta), e da sua máquina o script [`scripts/servidor.sh`](../../scripts/servidor.sh) manda o servidor baixá-la e reiniciar. O compose e o `.env.servidor` ficam na sua máquina e falam com o Docker do servidor por SSH, então o servidor não tem clone nem `.env`. O Dagster sobe como dois serviços (`webserver`: interface; `daemon`: agendamentos e sensores) e, a cada atualização, publica o lake e as docs. O script roda no Git Bash (Windows) e no Linux; todo subcomando aceita `--dry-run`, que só imprime os comandos.

Requisitos do servidor: Linux x86_64 com Docker e Compose, um usuário no grupo `docker`, acesso SSH (a porta pode não ser 22) e uma pasta de dados (por exemplo `/srv/dado-publico`). Com 8 GB de RAM compartilhados, crie swap (8 GB) e use `DADO_PUBLICO_MEM_LIMIT=4g` e `DADO_PUBLICO_DUCKDB_MEMORY=3GB` (modelo do `.env.servidor.example`; acima do que cabe, o DuckDB usa o disco: mais lento, sem estourar).

**Uma vez só, da pasta do repositório:**

1. `scripts/servidor.sh preparar usuario@host [porta]`: envia sua chave SSH (pede a senha uma vez, só se a chave ainda não autentica), cria o contexto Docker `servidor`, gera o `.env.servidor` a partir de [`.env.servidor.example`](../../.env.servidor.example) e do seu `.env` (copia só `DADO_PUBLICO_LAKE_URL` e `DADO_PUBLICO_R2_*`; nunca o Postgres; não imprime segredo) e confere o servidor: Docker e Compose, arquitetura, RAM e swap, espaço, pasta de dados gravável (tenta `sudo -n mkdir`; sem sudo, imprime o comando para você rodar) e porta da interface livre. Termina com um resumo `OK`/`FALTA`; pode rodar quantas vezes quiser. Revise o `.env.servidor` (pasta de dados, memória, `DADO_PUBLICO_PORT`, `DADO_PUBLICO_BIND`).
2. `scripts/servidor.sh dados`: copia `landing/`, `arquivos/` e `warehouse.duckdb` de `DADO_PUBLICO_STORAGE_ROOT` (padrão `./data_store`) para a pasta de dados do servidor. O landing só existe na máquina antiga (o R2 não o guarda, [ADR 0036](../05-decisoes/0036-r2-privado-fonte-da-verdade-do-que-nao-se-reconstroi.md)); `arquivos/` também se refaz do landing, mas leva cerca de 40 minutos. Feche tudo que use o warehouse local (Dagster, CLI, DBeaver): o script recusa se houver `warehouse.duckdb.wal`, e recusa também se o warehouse já existir no servidor, a menos que você passe `--forcar`. É idempotente: compara arquivos e bytes de cada pasta e só copia a que difere (`rsync` se existir nas duas pontas; senão `tar | ssh`, que recopia a pasta inteira).
3. `scripts/servidor.sh implantar`: baixa as imagens e sobe `webserver` e `daemon`. **Nunca lança o `atualizar_tudo` sozinho.**
4. Só na primeira vez: `scripts/servidor.sh primeira-carga` (aceita `--dry-run` e `--forcar`). Recusa se há execução em andamento, exige o warehouse no servidor, espera a interface e lança o `atualizar_tudo` uma vez (não lança de novo se já houve, salvo `--forcar`).

**Dois modos de primeira subida.** (a) *Restaurar do bucket e reconstruir*: sem warehouse para copiar, rode antes `dc run --rm daemon uv run --no-sync dado-publico rebuild` (`dc` na referência abaixo): restaura a identidade e o metadata do bucket privado (seção abaixo) e recarrega o raw do landing; cerca de seis horas, no `daemon` por causa do limite de memória. (b) *Copiar o warehouse e pular o rebuild*: o passo 2 já trouxe `warehouse.duckdb`; vá direto à `primeira-carga`.

**O `atualizar_tudo` não retoma.** Se falhar no meio, relançá-lo do início refaz tudo. O que pula o que já deu certo é **reexecutar a partir da falha** (interface, aba *Runs*, a execução que falhou, *Re-execute* a partir dos passos com falha). Iniciar o `atualizar_tudo` também tem custo: o Dagster grava centenas de eventos no SQLite, e em disco lento isso leva minutos antes do primeiro passo. A rotina não usa esse job: usa os menores (`captura_<fonte>`, `processar_tudo`, `publicar`).

**Servidor pequeno (8 GB compartilhados):** use `DADO_PUBLICO_MEM_LIMIT=4g` e `DADO_PUBLICO_DUCKDB_MEMORY=3GB` (padrões do `.env.servidor.example`) e crie swap. O dbt pós-identidade chegou a 6,5 GB sem limite; com limite, o DuckDB faz spill em disco (mais lento, sem estourar). **Isso não foi medido neste servidor**: meça o primeiro ciclo (aba *Runs* e `status`) antes de confiar no tempo total.

**Toda atualização** (depois do merge na `main` e do fim do workflow *Imagem*): `scripts/servidor.sh implantar`. Ele baixa as imagens e roda `up -d webserver daemon`; se houver execução em andamento (`STARTED`, `QUEUED` ou `STARTING`, consultada na GraphQL do próprio webserver), aborta, porque uma execução cortada no meio deixa a captura sem concluir (o `stop_grace_period` é de 2 minutos); `--forcar` ignora a trava. Para voltar a uma versão anterior, `DADO_PUBLICO_IMAGE_TAG=<sha do commit>` no `.env.servidor`. No VPS o mesmo comando pode virar um passo do workflow, com a chave SSH num segredo do GitHub.

**Acompanhar:** `scripts/servidor.sh status` mostra os containers, as três últimas execuções (estado, job, hora), a saúde dos daemons, as verificações de ativo em erro (consulta GraphQL, sem tocar no warehouse, vale com execução ativa), a memória e se a interface responde no endereço publicado (`DADO_PUBLICO_BIND` e `DADO_PUBLICO_PORT`, perguntado ao servidor por SSH). Na interface, a aba **Runs** lista as execuções e seus logs; é onde se vê a captura da noite e o ciclo das 04:00.

**Tag `dado_publico/refazer`:** os jobs `atualizar_*` levam essa tag. Ela manda o raw registrar uma atualização mesmo sem dado novo, e assim refaz tudo o que vem depois (staging, marts, identidade, export) a partir do que já está no raw. Sem a tag, só captura nova dispara a cadeia.

**Acesso à interface:** o Dagster aberto não tem login, então o compose publica a porta só em `DADO_PUBLICO_BIND` (padrão `127.0.0.1`, o próprio servidor). `DADO_PUBLICO_PORT` escolhe a porta (padrão 3000; o `preparar` avisa se estiver ocupada). Duas formas de abrir da sua máquina: túnel SSH (`ssh -L 3000:127.0.0.1:<porta> -p <porta ssh> usuario@host`, depois `http://localhost:3000`) ou, numa rede local confiável ou VPN, `DADO_PUBLICO_BIND=<IP do servidor na rede>` e `http://<IP>:<porta>`; nunca `0.0.0.0` num servidor exposto à internet.

> **Referência manual** (o que o script faz por baixo; `dc` = `docker --context servidor compose --env-file .env.servidor`, e **todo** comando compose precisa do `--env-file`, senão o compose lê o `.env` de desenvolvimento e age sobre o lugar errado): contexto `docker context create servidor --docker host=ssh://usuario@host:porta`; `dc pull webserver daemon` (`pull` sem nomes ignora serviços com perfil); `dc up -d webserver daemon`; lançar o job: `dc run --rm --no-deps -T daemon uv run --no-sync dagster job launch -m dado_publico_brasil.orchestration.definitions -j atualizar_tudo`. O `.env.servidor` define `COMPOSE_PATH_SEPARATOR=,` e `COMPOSE_FILE=compose.yaml,compose.servidor.yaml`. Valores com `$` (senhas) vão entre aspas simples.
>
> `DADO_PUBLICO_LAKE_URL` só vale junto com as chaves do R2: a validação do `export` falha de propósito se faltar alguma. O `init` roda só em `up`: se o host reiniciar, os serviços voltam com o manifesto da subida anterior (rode `implantar` depois de qualquer atualização de imagem). Builds locais (sem `--build-arg GIT_SHA`) gravam `versao_commit` `unknown`.

**Conferir:** `dc exec daemon uv run --no-sync dado-publico export --verificar`, `observe --email` (testa o SMTP) e a data do `manifesto.json` público.

**Manutenção:** os serviços reiniciam sozinhos (`restart: unless-stopped`) e o log do Docker é rotacionado (3 × 10 MB). Uma execução que passa de 24 h, ou que não inicia em 15 min, é marcada como falha (`run_monitoring` do `dagster.yaml`). O landing é o único dado sem cópia: faça backup periódico de `landing` em outro disco até haver cópia no bucket privado.

## Restaurar numa máquina vazia (bucket privado)

Com `DADO_PUBLICO_R2_BUCKET_PRIVADO` e as credenciais do R2 (`.env.example`), um warehouse novo (arquivo inexistente) restaura sozinho o `metadata` e a cópia mais recente e concluída da identidade, **com as mesmas chaves `id_pessoa`**, e avança as sequências. Depois: `uv run dado-publico rebuild` (sem `--old-warehouse`) e `run --historical` recapturam o raw das fontes.

- **Volta:** `id_pessoa` e suas ligações, o registro das capturas (URL, hash, data), execuções e testes.
- **Não volta sem o landing:** os arquivos. Eles são baixados de novo; o que a fonte mudou ou tirou do ar fica no `metadata` com o hash, e `verify` o aponta como ausente. Os lotes dos datasets por item (`foreach`) não se refazem iguais, e o acumulado dos datasets `merge` não volta (issue 155; nos `replace_partition` não há acumulado: o raw é a versão atual). Os arquivos de `arquivos/` se materializam de novo do landing.
- **Um escritor:** só a produção tem a variável e o token com escrita. O envio do `metadata` recusa sobrescrever um bucket com mais capturas que a máquina (restaure antes).

## Rodar por partes no container

O `dado-publico` roda igual dentro do container. Para um passo só, sem subir o agendador do Dagster (que lançaria execuções sozinho), pare o `daemon` e use um container avulso (no servidor, acrescente `--env-file .env.servidor`):

```bash
docker compose stop dagster
docker compose run --rm --no-deps -T dagster uv run --no-sync dado-publico transform
docker compose run --rm --no-deps -T dagster uv run --no-sync dado-publico export
docker compose up -d --no-build dagster   # religa depois
```

No Git Bash do Windows, prefixe com `MSYS_NO_PATHCONV=1` quando um argumento tiver caminho. O `transform` mostra uma linha por modelo e por teste (`12 of 340 OK ...`) e marca as fases (`== transform_pre`, `== transform_post`); para acompanhar uma execução longa, mande a saída para um arquivo e use `tail -f`. Para refazer só um modelo e o que depende dele (por exemplo, depois de uma falha de memória no meio da fase 2):

```bash
docker compose run --rm -T daemon uv run --no-sync python -c "
from dado_publico_brasil.core.settings import load_settings
from dado_publico_brasil.transformation import build
build.transform(load_settings(), 'transform_post', '--select', 'fct_candidaturas+', '--indirect-selection', 'cautious')"
```

Se o comando `dado-publico` do computador for bloqueado por política de aplicativo (erro "Controle de Aplicativo" no Windows), use `uv run python -m dado_publico_brasil.orchestration <comando>`.

### Recarregar uma captura ou um dataset

O arquivo e o hash no landing não mudam; só se marca a captura como não carregada e se carrega de novo:

1. `update metadata.capturas set dt_carga = null where fonte = '<dataset>' and particao = <ano>` (rode com `duckdb` ou `python` sobre o warehouse, com o pipeline parado).
2. `dado-publico load` (carrega só o que está pendente), depois `transform` e `export`.

Dataset com chave natural (candidaturas) se atualiza por `merge`. Dataset com chave por hash tem uma armadilha (próxima seção).

## Quando um modelo ou teste falha

Desenho no [ADR 0046](../05-decisoes/0046-publicacao-tolerante-a-falhas-de-nos-isolados.md). Nó isolado em erro **não** derruba o ciclo:

- **O que acontece.** O passo do dbt termina, grava o resultado e o tempo de todos os nós (também os com erro, aviso ou pulados, e também se o passo for interrompido) em `metadata.testes_resultados` e a execução em `metadata.execucoes` (`error`, com a duração real). A identidade, o dbt seguinte e a publicação seguem. O `export` **não publica versão nova** da tabela cujo modelo falhou ou foi pulado, nem da tabela com teste em erro; ela fica na versão anterior no lake. O restante sai.
- **Como ver.** Aba *Runs* do Dagster (uma linha de erro por nó), `dado-publico observe` e o e-mail do ciclo; no lake, `excluida_por` da tabela no `manifesto.json` e o aviso "versão anterior" no comentário da view do `catalogo.duckdb`. Consulta: `select id_no, resultado, mensagem from metadata.testes_resultados where resultado in ('error','fail') order by id_execucao desc`.
- **Como corrigir.** Corrija o modelo, o teste ou o dado; rode `processar_tudo` (ou `dado-publico transform`) e o `publicar`. A tabela volta a ser publicada e o `excluida_por` some. Falha do dbt sem nó reprovado (não iniciou) e falha da identidade ainda param o ciclo, sem publicar.
- **Limite.** Se um modelo `pre_identity` falhar, o Dagster pula o `dbt_post_identity` (ele depende das saídas daquele modelo): os marts ficam na versão anterior.

### Recarregar um dataset por mudança de chave

Mudou a chave (`primary_key`) do dataset, por exemplo para `_row_hash`? Nada a fazer: ao carregar, se a tabela do raw não tem uma coluna da chave, o `load_pending` descarta o dataset e o recarrega de todas as capturas vigentes do landing (o raw é espelho do landing), e registra `recarga_por_chave` em `metadata.fontes_verificacoes`. Pelo comando: `dado-publico load --rebuild --dataset <nome>` faz o mesmo à força. Dataset sem tabela ganha uma vazia (com as colunas declaradas), então os modelos do dbt rodam com zero linhas e os testes medem a lacuna. Se um dataset falhar ao carregar, o erro vai para `fontes_verificacoes` (`carga`) e os demais da fonte seguem.

## Armadilhas operacionais

Aprendidas na operação de 29 e 30/10/2026, com Docker Desktop no Windows:

- **Um container esquecido segura o warehouse.** O DuckDB aceita um escritor; um `dagster-run-*` ou o próprio `daemon` ainda ligado faz o próximo comando falhar com `Could not set lock on file ... Conflicting lock is held` ou `Permission denied`. Confira `docker ps -a`, pare o que sobrar e espere cerca de 20 segundos: o Docker libera a trava com atraso. Depois de matar um container, tente de novo antes de achar que o arquivo se corrompeu.
- **`Cannot allocate memory` ao ler ou escrever o warehouse não é falta de memória do DuckDB.** É o Windows com pouca RAM livre: o Docker acessa o arquivo por um compartilhamento do WSL. Feche programas pesados (navegadores, o aplicativo consumidor), libere o cache com `docker run --rm --privileged alpine sh -c "sync; echo 3 > /proc/sys/vm/drop_caches"` e refaça só o que falhou, como acima. O teto de 5 GB já está aplicado; o acompanhamento é a [issue 160](https://github.com/codigo-publico-brasil/dado-publico-brasil/issues/160).
- **Servidor pequeno e lento: o servidor de código do Dagster demora a subir.** No ciclo noturno o daemon registrou `Timed out waiting for gRPC server ... 180s` e `Could not reach user code server` (junto de `sqlite database is locked`, que é só a fila disputando o SQLite sob carga). O `dagster.yaml` declara `code_servers: {local_startup_timeout: 600, reload_timeout: 600}` (segundos; o aviso vinha aos 180 s), uma folga para a subida e a recarga do servidor de código. `local_startup_timeout` está na [referência do `dagster.yaml`](https://dagster.io/docs/deployment/oss/dagster-yaml) (seção `code_servers`); `reload_timeout` não está na página, mas existe no esquema da versão travada no `uv.lock` (a instância carrega com os dois). O `init` do compose copia esse mesmo arquivo a cada subida; o efeito só vale depois de reiniciar o daemon e o webserver. Se o aviso persistir, o servidor está subdimensionado: aumente memória e disco antes de aumentar o prazo.
- **Coluna nova em dataset com `primary_key: [_row_hash]` duplica o raw.** Votação e prestação de contas usam o hash da linha inteira como chave; acrescentar uma coluna ao contrato muda o hash de toda linha, e recarregar a captura **insere as linhas novas sem remover as antigas** (os votos contariam em dobro). Depois de recarregar, compare `count(*)` com `count(<coluna nova>)`, confirme que cada linha sem a coluna tem uma gêmea com ela e apague as antigas. Recarregue só o ano necessário. Acompanhamento: [issue 156](https://github.com/codigo-publico-brasil/dado-publico-brasil/issues/156).

## Reconstruir o warehouse do zero, a partir do landing

Quando o warehouse precisa ser refeito (mudança incompatível, arquivo corrompido, limpeza geral). O raw, o dbt e as consultas se refazem do landing; a identidade e o registro das capturas (URL, data, hash, ETag e itens de cada lote, em `metadata`, issue 153) não se refazem dele. Com o bucket privado configurado, vêm de lá (mesmas chaves; ignore o passo 2). Sem ele, o comando leva o `metadata` do warehouse antigo (`--old-warehouse`) e a **identidade é criada de novo, com chaves `id_pessoa` novas**; só faça isso se nenhuma aplicação guarda as chaves antigas.

1. **Pare tudo que escreve no warehouse**, em especial o Dagster (`docker compose stop webserver daemon`): uma imagem com código antigo apagaria as ligações novas da identidade.
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
| Todas as capturas carregaram | `uv run dado-publico query --sql "select count(*), count(dt_carga) from metadata.capturas"` (as duas contagens iguais) |
| O raw tem as mesmas linhas do antigo | compare `select count(*)` de cada tabela `raw_*` com o warehouse antigo (abra o antigo somente leitura com `duckdb`) |
| O landing está íntegro e a identidade tem cópia | `uv run dado-publico verify` |
| Nenhum teste do dbt reprova | `uv run dado-publico observe` (0 reprovados; a seção "Saúde por dimensão" mostra o resto) |
| Os modelos novos têm o tamanho esperado | `select count(*)` em `dim_pessoas`, `fct_mandatos`, `fct_eventos`, `agg_composicoes`, `fct_votos` contra o warehouse antigo |
| A identidade está sã | `dim_pessoas` e `identity.pessoas` com o mesmo número; nenhum mandato sem `id_pessoa` |
| O raw bate com o antigo | As diferenças esperadas são só de versões: o `load --rebuild` carrega a **versão mais recente** de cada arquivo, e a carga diária **soma** as versões nos datasets `merge` (issue 155; os `replace_partition` não somam). Fora disso, as contagens devem ser iguais; uma diferença de dobro é duplicação no antigo (foi o caso da votação de 2022) |
| Reconstruiu igual | rode `transform` de novo: nenhuma pessoa nova, nenhum snapshot novo |

5. Reconstrua a imagem do Dagster com o código atual (`docker compose --profile pipeline up -d --build`) antes de religá-lo.

## Onde o tempo da rotina vai

Depois de uma noite, três consultas respondem ([ADR 0044](../05-decisoes/0044-ciclo-rapido-staging-do-tse-em-tabela-e-tempos.md)): a duração de cada fase do dbt (`metadata.execucoes`, etapas `transform_pre`, `transform_post` e `freshness`, que medem o `dbt build` inteiro) e os nós mais lentos; e o `export` por tabela em `export_tempos.json`.

```bash
uv run dado-publico query --sql "SELECT id_no, tipo, qtd_segundos FROM metadata.testes_resultados WHERE id_execucao = (SELECT max(id_execucao) FROM metadata.execucoes WHERE etapa = 'transform_post') ORDER BY qtd_segundos DESC LIMIT 20"
```

O staging do TSE é tabela, recalculada no `transform_pre`: carregar o raw sem rodar o dbt deixa o staging do TSE com o raw anterior.

## Como saber o que está desatualizado

Dois tempos diferentes, os dois em `metadata.capturas`: `dt_captura` (quando **chegou conteúdo novo** da fonte) e `dt_verificacao` (quando o pipeline **perguntou** à fonte pela última vez). Dataset com `dt_verificacao` antigo está sem rodar; com `dt_captura` antigo mas verificação recente, a fonte é que não publicou nada.

```bash
uv run dado-publico query --sql "SELECT fonte, dataset, max(dt_captura) AS ultimo_dado_novo, max(dt_verificacao) AS ultima_verificacao FROM metadata.capturas GROUP BY 1, 2 ORDER BY 4"
```

Outras visões:

- **Ciclo noturno:** aba *Runs*: `processar_e_publicar` aparece uma vez por dia com dado novo; sem dado novo o tique é pulado (*Schedules* mostra o motivo do `SkipReason`). Lake do dia anterior = o ciclo não rodou ou falhou.
- **Dagster:** *Assets* mostra a última atualização de cada ativo e o atraso da captura (veja acima); a verificação `saude_da_fonte` mostra o último monitor da fonte (fora do ar, coluna que mudou, queda de volume).
- `dado-publico observe`: resumo da saúde das fontes, da carga e dos testes (falha se houver problema).
- **Frescor:** o dbt não mede mais o frescor (`dbt source freshness` foi retirado). Ele olhava `_dlt_load_id`, que só muda quando o **arquivo** muda: fonte estática (legislaturas, partidos) ficava em aviso para sempre. O atraso real é a **última verificação** (`metadata.capturas.dt_verificacao`, atualizada a cada captura mesmo sem mudança), medida por `max_age_days` do dataset (`dado-publico observe` e o relatório da carga) e pelo sensor `verificar_atrasos` do Dagster, que alerta quando uma captura agendada deixa de rodar. Fonte que parou de ser verificada continua alertando.

**O que ainda não existe:** um comando que pergunte às origens "há dado novo?" sem baixar. Hoje a pergunta é feita dentro da captura agendada (o pedido leve de `ETag`/`Last-Modified` antes de baixar), que roda no `schedule` de cada fonte. O alerta de atraso aparece na interface; o aviso por e-mail só cobre execuções que falham e exige SMTP configurado.
