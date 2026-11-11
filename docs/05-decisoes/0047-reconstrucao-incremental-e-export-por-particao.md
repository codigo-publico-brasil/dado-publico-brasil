# ADR 0047: Reconstruir só o que mudou (pular ramos, incremental por captura) e publicar só as partições alteradas

- **Status:** aceito (2026-11-11); passos 2 e 3 implementados no PR #242
- **Data:** 2026-11-06
- **Altera:** a Proposta B do [ADR 0044](0044-ciclo-rapido-staging-do-tse-em-tabela-e-tempos.md) (vira decisão, sem `dbt source freshness`) e o item "Tabela incremental" das alternativas dele (passa a valer para o staging do TSE); o item 5 do [ADR 0042](0042-ciclo-noturno-de-processamento-e-publicacao.md) (o ciclo deixa de ser tudo ou nada: roda só os nós com entrada nova); os itens 4 e 6 do [ADR 0035](0035-lakehouse-publico-no-r2.md) (impressão e envio por partição, manifesto versão 2). Convive com o [ADR 0046](0046-publicacao-tolerante-a-falhas-de-nos-isolados.md) (branch `ciclo-tolerante`, publicação por tabela).

## Contexto

O ciclo noturno reconstrói todo o dbt e calcula a impressão digital de todas as tabelas, mesmo sem dado novo. Medido no servidor (2 núcleos, HD 5400 rpm, DuckDB 2.0.0 com 3 GB):

- **dbt de 06/11** (staging do TSE já em tabela, ADR 0044): 4.993 s (fase antes da identidade 2.677 s, depois 2.316 s). Os nós que leem o TSE somam 95% do tempo dos modelos, e o raw do TSE **não muda desde 04/11** (`metadata.capturas`). Os quatro maiores: `stg_tse__votacao` 1.547 s, `fct_candidaturas` 1.228 s, `stg_tse__candidaturas` 456 s, `stg_tse__bens` 181 s.
- **Quem muda por noite** (capturas em `metadata.capturas`, 25/10 a 06/11): dos 10 dias com captura, Câmara e Senado em 9, DOU em 8, Transparência em 6, IBGE em 1; o TSE em 7, todos por pedido manual e nenhum depois de 04/11. Ou seja: **toda noite muda alguma coisa, quase nunca o TSE**. Por isso o `needs_cycle` (qualquer raw mudou, reconstrói tudo) não ajuda.
- **Export de 05/11** (staging do TSE ainda em view): impressões 1.933 s, escrita 1.876 s. Com o staging em tabela, a impressão de `stg_tse__votacao` (46,2 milhões de linhas) caiu de 1.701 s para **168 s** (medido em 06/11, leitura só de consulta no warehouse do servidor); a mesma impressão separada por `ano_eleicao` custou 99 s (uma varredura, todas as partições). O custo restante do export está em ler tabelas que não mudaram e em regravar a tabela inteira quando um ano muda.
- **Partição = captura no TSE:** em `stg_tse__votacao` cada `ano_eleicao` tem exatamente uma captura e uma URL (16 anos, 16 capturas; ADR 0043, `replace_partition`). Contar linhas por `id_captura` levou 0,3 s. O sinal de "qual partição mudou" já existe e é barato.
- **O que não fecha:** `int_tse_pessoas` liga candidaturas de anos diferentes pelo nome e nascimento (uma eleição nova pode mudar o `id_pessoa_tse` de uma de 2018); `fct_candidaturas` depende dele, da identidade e de `int_tse_eleitos`; `int_tse_eleitos` e `fct_mandatos` usam `year(current_date)` (mudam na virada do ano) e `agg_composicoes` usa o mês corrente. A identidade não criou pessoas nas últimas 8 execuções, mas quando cria pessoas, ligações ou fusões, muda `id_pessoa` sem o raw mudar.

## Decisão

O inventário de todos os modelos está no [anexo](#anexo-inventário); as classes são:

- **(a) estática ou pequena:** seeds. Só mudam com o código, que já força a reconstrução completa (item 4).
- **(b) incremental por captura:** os seis staging anuais do TSE (`votacao`, `candidaturas`, `bens`, `despesas_candidatos`, `receitas_candidatos`, `vagas`). (b\*) `fct_resultados` e `fct_campanhas` fecham por ano e ficam como candidatos de segunda fase, só se a medição pedir.
- **(c) pular o ramo inteiro quando nada a montante mudou:** todo o resto (90 modelos). É a classe que dá o ganho: sem TSE novo, pula 95% do tempo do dbt.
- **(d) depende da data:** `int_tse_eleitos`, `fct_mandatos` (ano) e `agg_composicoes` (mês). Entram quando o **período** muda, não toda noite; se entrassem toda noite, arrastariam `fct_candidaturas` (1.228 s) junto.

1. **Seleção por mudança de dado, do nosso lado.** Um passo antes de cada fase do dbt monta a lista de nós a construir a partir do `manifest.json` e do warehouse. Um nó entra se:
   1. alguma tabela do raw que ele lê (direta ou indiretamente) recebeu carga depois da **última construção com sucesso** dele: `max(dt_carga)` de `metadata.capturas` por fonte e dataset contra o horário do nó em `metadata.testes_resultados` (que já guarda status e tempo por nó);
   2. a identidade mudou depois dessa construção, e ele depende de `stg_identity__*` (item 2);
   3. o período de que ele depende mudou (classe d: tag `data_atual` com `meta.periodo: ano | mes`);
   4. a última execução dele não foi sucesso (erro, pulado ou ausente);
   5. e, em qualquer caso, **todos os descendentes** de quem entrou (`<nó>+`).
   `stg_metadata__capturas` não é gatilho (ganha linhas toda noite; quem decide é a fonte, como no 0044). Sem `dbt source freshness` (removido no PR #238) e sem `--state` (só detecta código). O passo chama `dbt build --select <lista>`; os testes dos nós escolhidos rodam junto (seleção indireta `eager` do dbt: teste de relação entra se um dos pais entrou).
2. **A identidade avisa quando muda.** O passo `identity` grava, antes e depois, uma impressão de `pessoas`, `pessoas_identificadores` e `pessoas_fusoes` (contagem e soma de `hash` da linha; tabelas pequenas, segundos) em `metadata.execucoes`. Impressão diferente = identidade mudou = item 1.2 seleciona `source:identity+`. Contar só pessoas criadas não basta: uma ligação nova muda `id_pessoa` sem pessoa nova.
3. **Incremental por captura no staging do TSE (classe b).** `materialized: incremental`, `incremental_strategy: delete+insert`, `unique_key: url_fonte` (a URL é o arquivo anual, estável entre capturas). Em modo incremental o modelo lê só as linhas do raw cujas capturas ainda não estão na tabela (`_source_file_id not in (select distinct id_captura from {{ this }})`); o dbt apaga as linhas das mesmas URLs e insere as novas. Um `post_hook` apaga as URLs que saíram do raw. Não se usa `microbatch` (ver Alternativas e o experimento). `on_schema_change: fail`: coluna nova pede `--full-refresh` do modelo, que o item 4 já dispara.
4. **Rede de segurança: reconstrução completa** (`dbt build --full-refresh` e impressão de todas as tabelas no export) quando: mudou o commit do código ou um seed (`versao_commit` diferente do da última completa); falta estado (primeira execução, warehouse novo); `--full` pedido; e **uma vez por semana** (domingo). Regra que nenhum otimizador pode quebrar: **nenhum nó é pulado se uma entrada dele mudou, e nenhum `id_pessoa` fica velho**; na dúvida, entra.
5. **Testes obrigatórios de equivalência** (pipeline sintético de `tests/support`, a cada PR que mexa nisso): para cada tabela de staging, intermediate e marts, o build parcial e o completo dão a mesma contagem e a mesma soma de `hash` por coluna nos cenários: nada mudou; só uma fonte mudou; um ano do TSE republicado (captura nova da mesma URL, com linhas a menos e a mais); uma URL retirada; a identidade ganhou uma ligação e uma fusão; virou o mês e o ano (data simulada por `var`). Testes do dbt sobre tabelas incrementais continuam rodando na **tabela inteira** quando o modelo entra (o dbt não filtra teste por lote); os caros podem ganhar `where` por partição depois, se a medição pedir.
6. **Export por partição.** 
   1. Tabela que **não foi construída** neste ciclo (fora da seleção do item 1, conferido no `run_results.json`) não tem impressão recalculada: reaproveita a entrada do manifesto anterior. Na reconstrução completa semanal, todas são recalculadas.
   2. Tabela com `meta.particao` grande: a impressão é por ano (`group by ano`, uma varredura) e o manifesto guarda, por partição, linhas, impressão e arquivos. Só os anos com impressão diferente são regravados (`COPY ... WHERE ano = X` para `ano=X/part-0.parquet`); o ano que sumiu tem o arquivo apagado **depois** da troca de manifesto e catálogo, como os órfãos de hoje.
   3. **Manifesto versão 2:** campo `versao_manifesto: 2` e, por tabela, a lista `particoes` (`ano`, `linhas`, `impressao`, `arquivos`). Os campos atuais (`arquivos`, `ano`, `linhas`, `impressao` da tabela) continuam, então quem lê a versão 1 e o `catalogo.duckdb` (que lista os arquivos) não muda.
7. **Com a publicação tolerante (0046):** o 0046 lê "a última execução de cada fase" para achar nós reprovados. Com seleção parcial, um nó pode não ter rodado nesta noite: vale o **último resultado de cada nó** (a mesma consulta do item 1.1). Nó em erro entra de novo na noite seguinte (item 1.4) e continua sem versão nova publicada até passar.

## Experimento (dados sintéticos)

Projeto dbt mínimo fora do repositório (dbt-core 1.12.6, dbt-duckdb 1.11.0, DuckDB 2.0.0), com um raw de votação em três URLs e a troca por captura do ADR 0043. Código do adaptador lido em `dbt/include/duckdb/macros/materializations/incremental_strategy/`.

- **`delete+insert`** com `unique_key` de uma coluna gera `delete from alvo where (url_fonte) in (select url_fonte from tmp)` e depois `insert`: troca a partição inteira, inclusive linhas que sumiram da fonte. Confirmado: republicar um ano (valor mudado, linha retirada, linha nova) deu tabela **idêntica** à reconstrução completa (contagem e soma de `hash` por coluna); a linha de 2016 que vinha no arquivo de outra URL foi preservada (um `unique_key` por ano a teria apagado); com o `post_hook`, retirar uma URL do raw também deu tabela idêntica; e `--full-refresh` depois disso deu o mesmo que o incremental.
- **`microbatch`** é `delete` + `insert` por intervalo de `event_time`, um comando por lote (na primeira construção, um lote por ano de `begin` até hoje: 11 consultas para 3 anos com dado). Confirmado: republicado 2016, a execução normal só refez 2025 e 2026 (`lookback`) e a tabela ficou **diferente** da completa; com `--event-time-start 2016-01-01` o ano voltou a bater, mas a URL retirada continuou lá (nenhum lote a apaga). O filtro por lote só entra na leitura de quem declara `event_time` (`... where dt_ref >= '2016-01-01' and dt_ref < '2017-01-01'` no SQL compilado); sem ele, cada lote lê a tabela de cima inteira. O raw não tem coluna de data (o ano é texto do arquivo), então cada lote leria o raw inteiro.
- **Testes do dbt** sobre o incremental: o SQL compilado do `not_null` lê a tabela inteira (`select votos from stg_inc where votos is null`), em toda execução em que o modelo entra.
- **Não confirmado:** tempo do `delete` de uma URL em 46 milhões de linhas no HD do servidor; se o `delete` e o `insert` correm na mesma transação no dbt-duckdb (uma queda entre os dois deixaria a URL sem linhas até a próxima execução, que a refaz porque a captura não estará na tabela); se o filtro de lote do `microbatch` atravessa a macro `tse_source` (irrelevante, pois ele foi descartado); e a equivalência do pulo de ramos no pipeline sintético do projeto, que só existe depois do passo 2 do plano.

## Alternativas consideradas

- **Manter tudo ou nada:** zero estado novo, mas 80 min de dbt por noite para recalcular um TSE que não mudou; o ciclo já ultrapassa a janela quando há carga.
- **Disco SSD no servidor:** ajuda tudo e não exige código; recomendável de qualquer forma, mas não muda a ordem de grandeza (ler 46 milhões de linhas que não mudaram continua sendo trabalho jogado fora). Não exclui este ADR.
- **`microbatch` do dbt:** escolhe os lotes pelo relógio (lote atual mais `lookback`), não pelo dado que mudou. O TSE republica anos passados (um `lookback` não pega 2022 em 2026 sem `--event-time-start`), o ano é inteiro e não data (precisa de coluna `event_time` artificial) e, sem `event_time` nos modelos de cima, cada lote lê o raw inteiro. Serve a fatos que chegam em ordem de tempo, não a fotos anuais republicadas.
- **`delete+insert` por ano (`unique_key: ano_eleicao`):** apaga pelo valor que vem no dado; o arquivo de um ano pode trazer linha de outro, e um ano apagaria linhas do outro (o mesmo motivo do 0043). A URL é a partição real.
- **`merge`:** compara linha a linha; mais caro e não resolve linha que sumiu da fonte.
- **`state:modified+` / `source_status:fresher+`:** o primeiro só vê código; o segundo exige `dbt source freshness`, que saiu do projeto. A data de carga já está em `metadata.capturas`.
- **Incremental só nos maiores (inclusive `fct_candidaturas`):** `fct_candidaturas` não fecha por ano (`int_tse_pessoas` liga anos, identidade, data). Fazê-lo incremental exigiria separar a agregação pesada da votação num intermediário por ano; fica para quando o TSE voltar a capturar com frequência e a medição mostrar que vale.

## Consequências e riscos

- **Estado novo a manter:** a última construção com sucesso por nó (já existe em `metadata.testes_resultados`), a impressão da identidade por execução e o commit da última reconstrução completa. Se qualquer um faltar, o ciclo é completo.
- **Risco de dado velho:** um nó pulado com entrada mudada. Mitigação: a regra do item 4, os testes do item 5 e a reconstrução semanal, que também mostra (por impressão) se algo divergiu: diferença numa tabela que não entrou na seleção é bug e vira teste.
- **Complexidade:** um passo de seleção (Python, agnóstico a fonte: usa só o manifesto e `metadata`), três modelos com tag de período e seis staging incrementais. Nenhuma dependência nova.
- Ganho estimado sem TSE novo: dbt de ~83 min para poucos minutos (os ramos da Câmara e do Senado mais a fase de identidade); export de horas para a impressão das tabelas reconstruídas. **Hipótese** até o passo 2 do plano medir.

## Plano de implantação (passos pequenos, um PR cada)

1. **Medir antes:** `qtd_segundos` das duas fases e `export_tempos.json` de uma noite com staging em tabela (base). Aceite: número no PR do passo 2.
2. **Seleção por mudança (itens 1, 2 e 4) e tag de período (classe d).** Aceite: testes de equivalência do item 5; numa noite sem TSE, `stg_tse__*` e `fct_candidaturas` não aparecem em `metadata.testes_resultados` daquela execução. Ganho: soma de `qtd_segundos` antes e depois.
3. **Export: pular a impressão do que não foi construído (6.1).** Aceite: manifesto idêntico ao do export completo no pipeline sintético; tempo da fase de impressões em `export_tempos.json`.
4. **Piloto incremental: `stg_tse__votacao` (item 3).** Aceite: equivalência com `--full-refresh` nos cenários de republicação e de URL retirada; tempo com um ano novo menor que o completo (medir com a carga de um ano).
5. **Manifesto v2 e escrita por partição (6.2 e 6.3), piloto `fct_candidaturas` e `stg_tse__votacao`.** Aceite: `verify` passa; consumidor da v1 lê o mesmo; republicar um ano grava só aquele `ano=`.
6. **Demais staging do TSE e, se a medição pedir, `fct_resultados` e `fct_campanhas`** (b\*), por custo.

## Registro de implementação (passos 2 e 3, PR #242)

Duas decisões da implementação diferem do texto acima; o resto vale como escrito.

- **A execução seletiva usa `--exclude` dos modelos pulados, não `--select` da lista a construir.** O `dagster-dbt` une o `--select` próprio com o que passamos e reconstruiria a fase inteira; vários `--exclude` se unem corretamente. Os modelos pulados chegam ao Dagster como `MaterializeResult` com metadado `pulado`, para o passo seguinte não ser pulado.
- **A identidade conta como mudada também quando a impressão difere entre duas etapas** (o "antes" desta execução contra o "depois" da anterior), não só antes e depois da etapa `identity`. A prova de equivalência mostrou que uma alteração feita fora da etapa (restauração, correção manual) deixava `id_pessoa` velho nos modelos pulados.
- Ainda não medido em execução real do Dagster; o ganho de tempo só aparece a partir da segunda noite depois do deploy.

## Anexo: inventário

Fontes: tempos do log do dbt (`dbt build`, modelo mais os testes ligados a ele) das execuções de 05/11 (staging do TSE em view) e 06/11 (em tabela); export de 05/11 (impressão + escrita, s); linhas do `manifesto.json` publicado em 05/11; dependências do `manifest.json` (`dbt parse`). "Ganho" é o tempo que deixa de ser gasto numa noite sem dado novo do TSE e sem mudança da identidade: MEDIDO para o dbt (é o tempo do nó), HIPÓTESE para o export (as impressões de 05/11 incluíam o cálculo das views). Os 25 mais caros pela soma do dbt de 06/11 e do export:

| # | Modelo | Camada | Mat. | dbt 05/11 (s) | dbt 06/11 (s) | export 05/11 (s) | Linhas | Data de referência | O passado fecha? | Identidade | Data atual | Classe | Ganho noturno sem dado novo |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `stg_tse__votacao` | staging | table | 361 | 1547 | 1701+0 | 46223082 | ano_eleicao | sim, por captura (o TSE pode republicar o ano) | não | não | b | ~1547 s dbt MEDIDO; export HIPÓTESE |
| 2 | `stg_tse__candidaturas` | staging | table | 89 | 456 | 1897+734 | 3687108 | ano_eleicao | sim, por captura (o TSE pode republicar o ano) | não | não | b | ~456 s dbt MEDIDO; export HIPÓTESE |
| 3 | `fct_candidaturas` | marts | table | 2626 | 1228 | 118+90 | 3685373 | ano da candidatura | não (liga anos ou pessoas) | sim | não | c | ~1228 s dbt MEDIDO; export HIPÓTESE |
| 4 | `stg_tse__bens` | staging | table | 21 | 181 | 470+280 | 5086567 | ano_eleicao | sim, por captura (o TSE pode republicar o ano) | não | não | b | ~181 s dbt MEDIDO; export HIPÓTESE |
| 5 | `stg_tse__despesas_candidatos` | staging | table | 0 | 125 | 193+270 | 7061670 | ano_eleicao | sim, por captura (o TSE pode republicar o ano) | não | não | b | ~125 s dbt MEDIDO; export HIPÓTESE |
| 6 | `fct_proposicoes` | marts | table | 52 | 49 | 94+58 | 890077 | dt_apresentacao | não (fonte atualiza registros) | não | não | c | ~49 s dbt MEDIDO; export HIPÓTESE |
| 7 | `int_tse_pessoas` | intermediate | table | 124 | 158 | 25+0 | 3536094 | - | não (liga anos ou pessoas) | não | não | c | ~158 s dbt MEDIDO; export HIPÓTESE |
| 8 | `dim_pessoas_cadastro` | marts | table | 76 | 160 | 1+2 | 8534 | - | não (liga anos ou pessoas) | sim | não | c | ~160 s dbt MEDIDO; export HIPÓTESE |
| 9 | `fct_resultados` | marts | table | 855 | 78 | 19+26 | 3687110 | ano da candidatura | sim, por ano | não | não | b* | ~78 s dbt MEDIDO; export HIPÓTESE |
| 10 | `fct_eventos` | marts | table | 38 | 19 | 55+46 | 3713405 | dt_evento | não (liga anos ou pessoas) | sim | não | c | ~19 s dbt MEDIDO; export HIPÓTESE |
| 11 | `stg_tse__receitas_candidatos` | staging | table | 1 | 15 | 67+30 | 1477100 | ano_eleicao | sim, por captura (o TSE pode republicar o ano) | não | não | b | ~15 s dbt MEDIDO; export HIPÓTESE |
| 12 | `stg_tse__vagas` | staging | table | 0 | 6 | 68+6 | 136084 | ano_eleicao | sim, por captura (o TSE pode republicar o ano) | não | não | b | ~6 s dbt MEDIDO; export HIPÓTESE |
| 13 | `fct_candidaturas_votos` | marts | table | 272 | 69 | 1+2 | 14332 | ano_eleicao | não (id_pessoa) | sim | não | c | ~69 s dbt MEDIDO; export HIPÓTESE |
| 14 | `fct_normas` | marts | table | 43 | 34 | 17+20 | 244027 | ano | não (fonte atualiza registros) | não | não | c | ~34 s dbt MEDIDO; export HIPÓTESE |
| 15 | `stg_senado__normas` | staging | view | 1 | 2 | 37+23 | 244027 | - | não (fonte atualiza registros) | não | não | c | ~2 s dbt MEDIDO; export HIPÓTESE |
| 16 | `stg_camara__proposicoes` | staging | view | 1 | 4 | 22+35 | 887338 | ano | não (fonte atualiza registros) | não | não | c | ~4 s dbt MEDIDO; export HIPÓTESE |
| 17 | `stg_camara__proposicoes_autores` | staging | view | 6 | 9 | 32+19 | 1808586 | - | não (fonte atualiza registros) | não | não | c | ~9 s dbt MEDIDO; export HIPÓTESE |
| 18 | `brg_proposicoes_autorias` | marts | table | 15 | 22 | 23+14 | 1808586 | - | não (id_pessoa) | sim | não | c | ~22 s dbt MEDIDO; export HIPÓTESE |
| 19 | `fct_campanhas` | marts | table | 39 | 20 | 9+14 | 1640561 | ano da candidatura | sim, por ano | não | não | b* | ~20 s dbt MEDIDO; export HIPÓTESE |
| 20 | `fct_emendas_favorecidos` | marts | table | 14 | 22 | 13+0 | 828563 | ano | não (fonte atualiza registros) | não | não | c | ~22 s dbt MEDIDO; export HIPÓTESE |
| 21 | `fct_pessoas_partidos` | marts | table | 19 | 12 | 8+13 | 941568 | ano_referencia | não (liga anos ou pessoas) | sim | não | c | ~12 s dbt MEDIDO; export HIPÓTESE |
| 22 | `fct_candidaturas_bens` | marts | table | 72 | 24 | 4+4 | 117709 | ano_eleicao | não (id_pessoa) | sim | não | c | ~24 s dbt MEDIDO; export HIPÓTESE |
| 23 | `int_tse_eleitos` | intermediate | table | 586 | 28 | 2+0 | 534065 | ano_eleicao | n/d | não | sim | d | ~28 s fora da virada do ano; MEDIDO |
| 24 | `stg_camara__deputados` | staging | view | 1 | 13 | 1+15 | 7889 | - | não (fonte atualiza registros) | não | não | c | ~13 s dbt MEDIDO; export HIPÓTESE |
| 25 | `int_vinculos_propostos` | intermediate | table | 161 | 27 | 0+0 | 15675 | - | não (liga anos ou pessoas) | não | não | c | ~27 s dbt MEDIDO; export HIPÓTESE |

- **Classe a** (7): `dim_cargos_posse`, `dim_cargos`, `dim_partidos`, `vinculos_aprovados`, `dim_evento_tipos`, `partidos_eventos`, `partidos_siglas`.
- **Classe c** (90; as views `app_` não existem mais, ADR 0041): `int_proposicoes_autorias_ligadas`, `fct_votos`, `fct_votacoes`, `int_votacoes_votos_ligados`, `dim_pessoas`, `fct_cargos_ocupacoes`, `stg_camara__votos`, `brg_orgaos_membros`, `int_ementas_siglas_extraidas`, `fct_emendas_convenios`, `stg_tse__fotos`, `fct_emendas`, `brg_frentes_membros`, `fct_normas_geradas`, `dim_constituicao_dispositivos`, `stg_transparencia__emendas_favorecidos`, `brg_normas_relacoes`, `fct_vetos`, `fct_normas_publicacoes`, `stg_camara__votacoes`, `fct_constituicao_alteracoes`, `int_tse_eleitos_grupos`, `dim_partidos_camara`, `fct_vetos_votos`, `stg_senado__votos`, `fct_vetos_dispositivos`, `int_votacoes_proposicoes_unidas`, `brg_votacoes_proposicoes`, `stg_camara__votacoes_objetos`, `brg_pessoas_ocupacoes`, `int_deputados_votos_agregados`, `dim_disputas`, `fct_exercicios`, `int_orgaos_membros_ligados`, `fct_proposicoes_tramitacoes`, `stg_camara__orgaos_membros`, `stg_camara__deputados_ocupacoes`, `stg_senado__exercicios`, `stg_camara__votacoes_proposicoes`, `fct_pessoas_fusoes`, `stg_senado__normas_publicacoes`, `stg_transparencia__emendas`, `int_senadores_unidos`, `dim_frentes`, `int_pessoas_unidas_cadastro`, `stg_senado__vetos`, `dim_partidos_linhagem`, `int_pessoas_vinculo`, `dim_territorios`, `stg_senado__votacoes`, `int_pessoas_atividade_agregada`, `stg_senado__senadores`, `stg_camara__votacoes_orientacoes`, `stg_senado__normas_relacoes`, `int_senado_materias_unicas`, `dim_legislaturas`, `stg_camara__deputados_detalhe`, `int_pessoas_profissoes_agregadas`, `dim_eleicoes`, `dim_municipios_codigos_tse`, `int_frentes_membros_ligados`, `stg_senado__vetos_votos`, `int_pessoas_senado_unidas`, `stg_transparencia__compras_itens`, `stg_camara__deputados_profissoes`, `stg_constituicao__linhas`, `stg_camara__deputados_historico`, `stg_camara__legislaturas`, `stg_senado__senadores_detalhe`, `stg_camara__frentes`, `stg_camara__frentes_membros`, `int_deputados_frentes_fotos`, `int_pessoas_ids_vistos`, `stg_ibge__municipios`, `stg_camara__tramitacoes`, `stg_camara__partidos`, `int_deputados_ids_unidos`, `stg_camara__orgaos`, `dim_orgaos`, `dim_municipios`, `stg_identity__pessoas_fusoes`, `stg_senado__processos`, `stg_identity__pessoas`, `stg_transparencia__emendas_convenios`, `stg_senado__vetos_dispositivos`, `stg_metadata__capturas`, `stg_identity__pessoas_identificadores`, `stg_transparencia__despesas`, `stg_transparencia__compras_termos_aditivos`, `stg_transparencia__compras`.
- **Classe d** (2 + `int_tse_eleitos` acima): `fct_mandatos` (ano), `agg_composicoes` (mês).

Soma do dbt de 06/11 por classe (modelo + testes ligados, s): a 4, b 2330, b* 99, c 2246, d 41; total 4720.
