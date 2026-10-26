# ADR 0027: Orquestração automática: schedule por fonte, propagação e serviço contínuo

- **Status:** aceito (2026-10-26, pelo fundador)
- **Data:** 2026-10-26
- **Substitui em parte:** o [ADR 0024](0024-regras-de-extracao-por-fonte.md) (`refresh: daily | on_request` vira `schedule`). Mantém dele: carga só da partição em curso e a pergunta barata à fonte antes de baixar.
- **Depende de:** [ADR 0006](0006-adotar-dlt-dbt-e-dagster.md) (Dagster) e [ADR 0014](0014-warehouse-lake-duckdb-e-postgres-de-servico.md) (DuckDB calcula, PostgreSQL serve).

## Contexto

O Dagster tinha um único agendamento (todo dia, às 6h, sobre todos os ativos), desligado por padrão. Nada disparava o que dependia de um dado novo: o dbt rodava junto, todo dia, e a publicação no PostgreSQL era um comando manual. Não havia cadência por fonte, jobs por contexto, aviso de atraso nem um jeito de manter o serviço ligado sem terminal aberto. Nem toda base muda todo dia (o TSE muda em datas pontuais).

## Decisão

1. **`schedule` por fonte, no YAML.** Um cron de 5 campos (fuso America/Sao_Paulo) no topo da declaração substitui `refresh`. O Dagster gera um agendamento `captura_<fonte>` por fonte, ligado por padrão. Sem `schedule`, a fonte só roda quando pedida. Fontes de datas pontuais (TSE) usam cadência semanal: a pergunta à fonte (`ETag`, `Last-Modified`) evita baixar o que não mudou.
2. **Jobs por contexto, gerados de `sources/`:** `captura_<fonte>` (landing e raw), `atualizar_<fonte>` (tudo o que vem da fonte, até a publicação) e `atualizar_tudo`.
3. **Propagação automática.** Os modelos do dbt, a identidade e a publicação usam `AutomationCondition.eager()`: rodam quando uma dependência recebe dado novo. O raw só registra atualização quando carregou captura nova, então sem dado novo nada a jusante roda.
4. **Publicação como ativo** (`servico/marts`), depois dos marts, quando `DADO_PUBLICO_POSTGRES_DSN` está definido: o PostgreSQL não fica atrás do warehouse.
5. **Atraso visível:** uma verificação de frescor por fonte agendada sobre o `landing/<fonte>`, com limite de 1,5 intervalo do cron.
6. **Uma execução por vez** (`dagster.yaml`, fila com `max_concurrent_runs: 1`), porque o DuckDB em arquivo aceita um escritor.
7. **Serviço contínuo:** `Dockerfile` e o serviço `dagster` do `compose.yaml` (perfil `pipeline`), que escuta só em `127.0.0.1`.

## Alternativas consideradas

- **Um agendamento só, mais jobs manuais (o que havia):** simples, mas exige mão humana e retransforma tudo sem necessidade.
- **Sensores por fonte que perguntam "há dado novo?":** mais código por fonte; a captura agendada já faz a pergunta barata.
- **Propagar por job (selecionando o downstream no agendamento):** roda o dbt mesmo sem dado novo. A condição `eager` roda só quando há.
- **Agendar com `cron` do sistema ou CI:** perde linhagem, interface e fila.

## Consequências

- Mudar a cadência é editar uma linha do YAML; fonte nova ganha agendamento, jobs e atraso sem código.
- O Dagster só propaga a partir do que ele materializou: na primeira vez é preciso rodar `atualizar_tudo`.
- O Dagster de código aberto **não tem login**. Enquanto não houver uma camada de autenticação na frente (decisão em aberto), a interface fica só em `127.0.0.1`.
- Não há ainda cadência semanal/mensal diferente por dataset dentro da mesma fonte, nem alerta de atraso por e-mail (só pela interface).
- A imagem Docker ainda não foi construída e testada de ponta a ponta.
