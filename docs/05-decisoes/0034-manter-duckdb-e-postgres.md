# ADR 0034: manter DuckDB como warehouse e PostgreSQL como serviço

- **Status:** proposto (2026-10-29); decisão do fundador na conversa de 29/10/2026
- **Data:** 2026-10-29
- **Confirma:** [ADR 0014](0014-warehouse-lake-duckdb-e-postgres-de-servico.md). Encerra as issues #31 (experimento com DuckLake) e #123 (um arquivo DuckDB ou vários).

## Contexto

Depois de crescer para cerca de 9,5 GiB e 79 milhões de linhas no raw, três caminhos foram avaliados: DuckLake (catálogo SQL sobre Parquet), um arquivo DuckDB por ciclo de vida (`raw`, curado, `identity`) e PostgreSQL como único banco. O DuckDB aceita um só escritor por vez, e a leitura fica bloqueada durante a carga; foi o único atrito real medido.

## Decisão

Fica a arquitetura do ADR 0014: um arquivo DuckDB, um escritor, e PostgreSQL só para servir. Não migramos nem experimentamos agora.

## Alternativas consideradas

- **DuckLake (v1.0, abril de 2026):** não tem chave primária, chave estrangeira nem índice, e só grava Parquet. A identidade de pessoas depende de chaves e de uma sequência. O suporte do dbt não foi confirmado. Ganharia versionamento por data, que hoje não é requisito.
- **Um arquivo por ciclo de vida:** isola a identidade e libera a leitura durante a carga, ao custo de configurar dlt e dbt por arquivo. O ganho não compensa a estrutura extra.
- **Só PostgreSQL:** cerca de 320 pontos de SQL específico do DuckDB em 128 modelos, e uma consulta analítica sobre dezenas de milhões de linhas fica mais lenta.

## Consequências

- Backup da identidade e do landing (#36) e proveniência ao lado do landing (#153) passam a ser a proteção do que não se reconstrói.
- **Gatilhos para reabrir:** o bloqueio de leitura durante a carga virar impedimento real para uma aplicação, a escrita concorrente se tornar necessária, ou uma exigência de "como era conhecido em tal data" (versionamento) que a modelagem de datas não resolva. O ADR 0014 mantém os portões de 300 GB e de 6 h.
