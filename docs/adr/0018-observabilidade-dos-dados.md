# ADR 0018: Observabilidade dos dados com Elementary e relatório por e-mail

- **Status:** aceito (2026-10-24, pelo fundador)
- **Data:** 2026-10-24

## Contexto

Os testes do dbt só pegam o que alguém previu. Precisamos achar de forma automática, e sem ninguém olhando, problema de lógica (junção que multiplica ou perde linhas), da origem (formato que muda, arquivo parcial) e da ingestão (linhas rejeitadas). Uma primeira versão com módulo próprio de fotografia de tabelas foi trocada por uma ferramenta dedicada.

## Decisão

1. **Elementary (Apache-2.0), como pacote dbt**, nos marts: `volume_anomalies`, `schema_changes` e `all_columns_anomalies` (nulos), todos com `severity: warn` para não bloquear o pipeline. O resultado de cada teste vai para `metadata.dbt_results`, e o Elementary guarda o histórico no esquema `elementary` do warehouse. Os testes entram uma vez por mart, no YAML, por âncora.
2. **Relatório HTML do Elementary sob demanda** com o `edr`, rodado por `uvx` (sem entrar nas dependências do projeto: ele traz bibliotecas de nuvem que não usamos, cerca de 600 linhas no `uv.lock`).
3. **Duas camadas nossas**, porque o Elementary só enxerga o que o dbt constrói: o monitor das fontes (disponibilidade, cabeçalho, volume) e o balanço de cada carga (`carga`), ambos em `metadata.source_checks`.
4. **`plataforma observe`** junta tudo (fontes e carga, testes do dbt, anomalias dos marts) e falha com código 1 se houver problema.
5. **Alerta por e-mail** por SMTP, configurado no `.env` (`PLATAFORMA_SMTP_*`, `PLATAFORMA_ALERT_*`), enviado ao fim da fase de marts se houver problema. O Elementary só alerta por Slack e Teams; e-mail é nosso, com `smtplib` da biblioteca padrão, sem dependência nova.

## Alternativas consideradas

- **Great Expectations e Soda:** repetem o que o dbt e o Elementary cobrem.
- **DataHub e OpenMetadata:** catálogos pesados, com serviços próprios; não compensam neste porte.
- **Soluções comerciais:** contrariam o projeto totalmente aberto.
- **Módulo próprio de fotografia e comparação:** funcionava, mas era código e limiares nossos para manter.

## Consequências

- A detecção de anomalia de volume precisa de cerca de 7 execuções de histórico para ter base de comparação; antes disso não alerta.
- O Elementary só cobre tabelas que o dbt constrói (staging, intermediate, marts); o `raw` é coberto pelo balanço da carga.
- A primeira execução baixa o pacote (`dbt deps`, automático); depois não precisa de rede.
- O relatório HTML precisa do warehouse livre (nenhum pipeline rodando).
