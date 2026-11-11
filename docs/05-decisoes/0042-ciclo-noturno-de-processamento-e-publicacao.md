# ADR 0042: Ciclo noturno: capturas escalonadas, um processamento e uma publicação por dia

- **Status:** aceito em 2026-11-11 (implementado; antes proposto (2026-11-04), para revisão do fundador)
- **Data:** 2026-11-04
- **Altera:** o [ADR 0027](0027-orquestracao-automatica-por-fonte.md), no item 3 (propagação por evento, `AutomationCondition.eager` e o sensor `propagar_atualizacoes`) e nos horários das capturas. Mantém do 0027: `schedule` por fonte no YAML, jobs gerados de `sources/`, publicação como ativo, atraso visível e uma execução por vez.

## Contexto

O fundador quer acordar com o lake atualizado: capturar de madrugada e publicar ao fim de tudo. Com a propagação por evento, cada captura que trazia dado novo disparava dbt, identidade, export e docs. Com seis fontes agendadas entre 06:00 e 08:00 isso podia somar vários ciclos pesados por manhã, cada um recalculando quase o mesmo, e a publicação (`publicacao/lake` e `publicacao/docs`) rodava no meio das capturas, sem ponto final definido. O servidor é pequeno (8 GB compartilhados, 4 GB para o container, uma execução por vez em `dagster.yaml`), e o dbt pós-identidade é a etapa mais pesada.

## Decisão

1. **Capturas escalonadas de madrugada** (fuso America/Sao_Paulo, `schedule` no YAML de cada fonte): camara 01:00, senado 01:20, transparencia 01:40, constituicao 01:50, dou 02:00, ibge dia 1 às 02:10. Cada uma é leve (incremental) e a fila é de uma execução, então uma espera a anterior. **O TSE não captura na rotina** (a eleição passou): sem `schedule`, só roda quando pedido (`captura_tse`, `atualizar_tse`); reativar é reintroduzir o cron no YAML. Ele continua no ciclo a jusante com o que já está no raw.
2. **Um ciclo único, `processar_e_publicar`, às 04:00** (`pipeline.CYCLE_CRON`), que roda o job `processar_tudo`: dbt, identidade, dbt pós-identidade, export do lake e docs, na ordem das dependências. A publicação é o **último passo**, e `publicacao/*` só sai daí e do job manual `publicar`. Nenhum agendamento nem sensor a dispara fora disso.
3. **Sem propagação por evento.** Saem `AutomationCondition.eager` (dbt, identidade, publicação) e o sensor `propagar_atualizacoes`. Ficam os sensores de falha de execução e de atrasos.
4. **No máximo uma vez por dia com sucesso, mas falha se repete.** Cada agendamento (as capturas e o ciclo) consulta o armazenamento do Dagster antes de executar: se o job já teve uma execução `SUCCESS` (ou ainda em andamento ou na fila) desde 00:00 local, devolve `SkipReason`; se só falhou (ou não houve), executa. Assim um tique atrasado ou repetido não recalcula o que já deu certo, e uma falha pode ser relançada, à mão ou por um tique posterior. Não se usa `run_key` por dia: ele bloquearia o reenvio até depois de uma falha. `dagster.yaml` desliga `run_retries` de forma explícita; os sensores de falha só avisam.
5. **O ciclo pula quando nada mudou.** O ciclo só roda se alguma tabela do raw registrou atualização depois do passo mais antigo do último ciclo completo (identidade e docs). A leitura é do log de eventos do Dagster, sem abrir o warehouse no daemon. Ciclo que falhou no meio (docs sem atualizar) roda de novo na noite seguinte.
6. **Erro numa captura não impede o ciclo:** são execuções independentes; o ciclo roda com o que há no raw, e o atraso aparece na verificação de frescor e no aviso da execução que falhou.

Base (Dagster 1.13.28, lida no código instalado, `dagster/_scheduler/scheduler.py` e `_core/instance/config.py`): a função de um agendamento pode devolver `RunRequest` ou `SkipReason`; o daemon só deduplica execuções pelo mesmo tique (a busca casa o horário agendado, além do `run_key`), então `run_key` por dia não impede um segundo tique no dia; `run_retries` é desligado por padrão; o daemon recupera até 5 tiques perdidos (`DEFAULT_MAX_CATCHUP_RUNS`), o que a consulta de sucesso do dia evita que vire 5 execuções. A fila de uma execução por vez é o `QueuedRunCoordinator` com `max_concurrent_runs: 1`.

## Alternativas consideradas

- **Manter `eager`:** o lake atualiza logo após cada captura, mas pode haver vários ciclos por noite, a publicação não tem fim definido e o servidor pequeno os enfileira.
- **`eager` com janela (`in_latest_time_window`) ou condição própria "depois que todas as capturas terminarem":** menos ciclos, mas a condição é mais difícil de ler e de testar, e o avaliador do Dagster roda no daemon a cada tique.
- **`run_key` por dia:** a deduplicação do Dagster casa também o horário do tique, então ela mal evita o que a consulta já evita, e bloquearia a repetição depois de falha.
- **Ciclo noturno (escolhido):** previsível, um ponto de publicação, simples de explicar e de auditar.

## Consequências

- O lake publicado é o de ontem para dados que chegam depois das 04:00; sem ciclo imediato quando o dado chega. O job manual `atualizar_<fonte>` (captura até publicação) continua para quem não quer esperar.
- Com a otimização, o dbt só roda na noite em que o raw recebeu dado; sem ela rodaria toda noite.
- A janela de 01:00 às 04:00 precisa caber nas capturas: uma captura longa (carga histórica) adia o ciclo, que espera na fila, e o lake sai mais tarde.
- Memória: o dbt pós-identidade chegou a 6,5 GB sem limite; com `DADO_PUBLICO_MEM_LIMIT=4g` e `DUCKDB_MEMORY=3GB` ele usa o disco. Não foi medido neste servidor.
- Não há alerta por e-mail sem SMTP configurado; a falha aparece na interface (aba Runs) e em `scripts/servidor.sh status`.
