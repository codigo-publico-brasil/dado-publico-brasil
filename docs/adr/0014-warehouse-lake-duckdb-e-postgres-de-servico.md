# ADR 0014: Warehouse em camadas: arquivos e DuckDB calculam, PostgreSQL serve

- **Status:** aceito (2026-10-23, pelo fundador)
- **Data:** 2026-10-23
- **Altera:** [ADR 0002](0002-pilha-tecnologica.md) (dados curados em PostgreSQL; lakehouse descartado) e o próximo passo do [ADR 0009](0009-repositorio-de-dados-pacote-unico.md) (dbt com macros de portabilidade para o PostgreSQL).
- **Desenho completo (componentes e infraestrutura):** [`../engenharia/arquitetura-producao.html`](../engenharia/arquitetura-producao.html)

## Contexto

Hoje o warehouse tem 1,4 GiB e o landing 3,1 GB; a maior tabela tem 2,2 milhões de linhas. O volume atual não decide nada. O roteiro traz fontes de outra ordem de grandeza (despesas e notas do Executivo, CNPJ, processos do Judiciário, estados e municípios), e o estado precisa de quatro cargas distintas: arquivo bruto imutável, transformação analítica, consulta de aplicações e busca em documentos.

## Decisão

1. **Landing e dados curados são arquivos num armazenamento de objetos** compatível com S3. O landing já é assim; os curados passam a ser Parquet quando o volume pedir (item 6).
2. **A transformação é do DuckDB com dbt** (um nó, um escritor, pipeline serializado). O dbt roda **só** no DuckDB: não há macros de portabilidade para o PostgreSQL.
3. **O PostgreSQL é a camada de serviço.** Recebe só os `marts` (e `documents` com pgvector), prontos e indexados, por um passo de publicação. As aplicações leem dele com papel somente leitura e nunca do DuckDB.
4. **A identidade (`id_pessoa`) fica no DuckDB e ganha *snapshot* imutável a cada execução** no armazenamento de objetos, com teste de restauração. As chaves já entregues a aplicações não podem mudar.
5. **O armazenamento de objetos, o servidor e o PostgreSQL são componentes, não produtos:** o código fala S3 e SQL padrão; a nuvem (ou servidor próprio) é decisão posterior.
6. **Portões de revisão, medidos e não presumidos:** (a) o arquivo DuckDB passar de ~300 GB ou uma execução completa passar de ~6 horas: exportar os curados para Parquet particionado e ler por ele; (b) um dataset não caber num nó (provável: Judiciário): movê-lo, só ele, para ClickHouse ou Trino, mantendo o contrato dos marts; (c) o PostgreSQL de serviço passar de ~500 GB ou de carga de leitura que pese: réplica de leitura e particionamento; (d) auditoria por versão, estado fora do disco local ou escrita concorrente virarem necessidade: rodar o experimento do DuckLake. Os limites numéricos são hipóteses a corrigir pela medição.
7. **Antes de implementar cada fonte nova, medir o tamanho dela** e registrar em `docs/dados/fontes-de-dados.md`.

## Alternativas consideradas

- **Só PostgreSQL (recomendada na primeira rodada, e abandonada):** a menor estrutura hoje, mas sem folga para centenas de milhões de linhas, e reescrever depois custa mais.
- **ClickHouse como warehouse:** excelente para varrer, fraco em atualizar e fundir linhas (a identidade faz isso) e com dbt menos maduro.
- **Trino ou Spark com Iceberg:** escala que não temos, operação pesada.
- **BigQuery, Snowflake:** não são código aberto e prendem a infraestrutura.
- **DuckLake (catálogo no PostgreSQL, dados em Parquet):** não adotado agora, por ser estrutura nova sem necessidade medida e por maturidade não verificada. É o candidato natural para trocar o trio "arquivo DuckDB, snapshots de identidade e exportação para Parquet", porque traz versões consultáveis (auditoria por data) e tira o estado do disco local, além de escrita concorrente. Revisitar com um experimento curto e isolado, depois que o PostgreSQL local existir, que teste o `dbt-duckdb`, o `dlt` e a fusão de identidade, com critérios de aprovação e descarte definidos antes de rodar.

## Consequências

- Dois motores para operar (DuckDB no servidor de processamento, PostgreSQL de serviço) e um passo de publicação.
- A escrita no DuckDB é única; o executor do Dagster continua sequencial.
- O caminho "dbt no PostgreSQL" e as macros de portabilidade saem do roteiro.
- O backup do `identity` passa a ser requisito de operação, não opcional.
- A infraestrutura (servidor, armazenamento, PostgreSQL, rede, segredos, observabilidade, backup) fica descrita por componente, independente de provedor.
