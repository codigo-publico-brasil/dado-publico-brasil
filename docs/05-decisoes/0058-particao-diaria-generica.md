# ADR 0058: Partição diária genérica (`partition: day`)

- **Status:** proposto
- **Data:** 2026-11-12
- **Complementa:** [ADR 0045](0045-meses-fechados-405-e-pacote-unico.md) (a partição mensal e o `lag_months`) e [ADR 0053](0053-nucleo-sem-nomes-de-fonte.md) (o núcleo declara o calendário no YAML, sem nomear fonte).
- **Para quem é:** quem declara uma fonte que publica um arquivo por dia ou revisa o núcleo. Responde: como o contrato pede um arquivo por dia sem tocar no núcleo.
- **Origem:** Refs #11.

## Contexto

Há fontes que publicam um arquivo por dia (um zip por dia útil, poucos KB no fim de semana e no feriado). O contrato só tinha partição `year`, `month` e `sequence`, e um zip por dia não cabe em nenhuma.

## Decisão

1. `partition: day`, com `first_day: AAAAMMDD` (obrigatório) e `lag_days: N` (opcional, padrão 0: dias de atraso até o arquivo existir). O valor da partição é o dia como `AAAAMMDD` (inteiro, como o mês é `AAAAMM`); a URL usa `{day}` (ou `{partition}`; `{year}` e `{month}` seguem sendo esse mesmo valor). Vale também em `files.path` (`{partition}`).
2. O último dia pedido é `hoje - lag_days`: dia futuro nunca é pedido. `on_demand` e `max_age_days` funcionam como nas outras partições.
3. **Janela:** o plano normal vai de `first_day` ao último dia. Quem quer um histórico anterior declara outro dataset `on_demand` com outro `first_day`.
4. **Plano incremental:** só o último dia (um HEAD se nada mudou). Os dias que faltam entram pela recuperação (`plan_recovery`), que **não aplica o limite por execução** a datasets diários: a janela já foi escolhida no YAML.
5. **404:** o dia sem arquivo é `nao_encontrado` e vira indisponível (não é tentado de novo sem pedido); no dia mais recente é `nao_publicado`, e ele e o anterior seguem sendo pedidos, como o mês anterior na partição mensal.

## Alternativas

- Um dataset mensal que baixa vários arquivos: descartada, a captura é um arquivo por URL e por partição (hash e data no landing).
- `lag_days` como `lag_months` em dias úteis: descartada, feriado é calendário da fonte; o 404 já cobre o dia sem arquivo.
- Limite de recuperação também nos dias: descartada, a janela do YAML já limita e um limite de 3 por execução levaria semanas para fechar a lacuna.

## Consequências

Fonte diária entra só com YAML. Janela larga com `rate_limit` baixo leva muitas execuções: a recuperação continua de onde parou (idempotente).
