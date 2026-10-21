# ADR 0002: Pilha tecnológica do piloto

- **Status:** aceito (2026-10-19, pelo fundador)
- **Data:** 2026-10-19
- **Contexto do projeto:** uma pessoa desenvolvendo com apoio de agentes de IA, com cerca de 10 horas por semana. Fases 0 a 2 precisam de dados confiáveis e páginas rápidas, não de escala.

## Contexto

Antes do primeiro código, é preciso fixar linguagem, banco, orquestração, busca, web e hospedagem. O volume do piloto é pequeno (decisões nacionais e um município), e o maior risco do projeto é escopo e manutenção, não desempenho. A pilha deve ser pequena, ter poucas peças para operar e permitir que o fundador aprenda engenharia de dados de verdade.

## Decisão

| Área | Escolha |
| --- | --- |
| Linguagem | Python |
| Dados curados | PostgreSQL |
| Originais imutáveis | Armazenamento de objetos S3-compatível, com hash, URL e data de captura |
| Pipelines | Dagster (ativos de dados, testes e linhagem) e dbt-core (transformações em SQL) |
| Busca | Texto completo e pgvector no próprio PostgreSQL |
| Web | Páginas renderizadas no servidor, com URL permanente por entidade, cacheadas em CDN |
| Forma do código | Monolito modular em um repositório (ingestão, curadoria, API, web, assistente, notificações) |
| Hospedagem | Uma VM em nuvem brasileira, Docker Compose e infraestrutura como código |

## Alternativas consideradas e o que cada escolha custa

- **Lakehouse (Parquet e Iceberg) no lugar de PostgreSQL:** mais escala, mais peças. Descartado até que a fase 1 meça que o Postgres não basta.
- **Airflow ou cron no lugar de Dagster:** Airflow é mais conhecido e mais pesado; cron é mais simples e não dá linhagem nem testes por tabela. Dagster custa uma curva de aprendizado maior e é o que melhor serve ao requisito "do número na tela ao documento original".
- **OpenSearch no lugar de busca no Postgres:** um serviço a mais para operar. Troca-se quando relevância ou volume exigirem.
- **SPA com API no lugar de páginas no servidor:** pior em celular simples, pior para compartilhar e indexar.
- **Kubernetes desde o início:** aprendizado, não necessidade. Entra na fase 6, se justificar.

## Ferramentas de desenvolvimento (decididas em 2026-10-19)

| Área | Escolha |
| --- | --- |
| Dependências e ambiente | uv (venv, lockfile e versão do Python em uma ferramenta) |
| Lint e formatação | Ruff |
| Tipos | mypy |
| Testes | pytest |
| Varredura de segredos | gitleaks, no CI |

Alternativas descartadas: Poetry (mais lento, mais peças), pip com venv (sem lockfile nativo), pyright (exige Node), trufflehog (mais pesado).

## Fora deste ADR (a decidir em ADR próprio)

1. **Framework web em Python** (por exemplo FastAPI com templates, ou Django), antes da fase 2.
2. **Fornecedor de armazenamento de objetos e da VM** (nuvem brasileira), conforme preço e disponibilidade.
3. **Medir na fase 1** se o PostgreSQL comporta o volume e a busca vetorial; a hipótese só vale até a medição.

## Consequências

- Cada dependência listada acima conta como aprovada por este ADR quando ele for aceito; qualquer outra exige ADR novo (regra do `AGENTS.md`).
- Poucas peças para operar: PostgreSQL, objetos, Dagster e a aplicação.
- Trocar uma peça (busca, orquestração, banco) fica barato porque os módulos têm fronteira explícita.
- Depois de aceito, este ADR não é editado: a mudança vira um ADR novo que o substitui.
