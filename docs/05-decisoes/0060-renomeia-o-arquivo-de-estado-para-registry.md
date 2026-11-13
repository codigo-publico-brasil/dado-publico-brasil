# ADR 0060: Renomeia o arquivo de estado para `registry`

- **Status:** proposto
- **Data:** 2026-11-13
- **Altera em parte:** o [ADR 0051](0051-raw-em-parquet-por-captura-e-estado-em-arquivo-proprio.md) (só o nome do arquivo e do alias; a separação em arquivo próprio segue).
- **Para quem é:** quem opera ou consulta o lake. Responde: por que `estado.duckdb` virou `registry.duckdb` e como o arquivo existente é adotado sem perda.

## Contexto

O ADR 0051 pôs `metadata` e `identity` num arquivo próprio, `estado.duckdb`, anexado ao warehouse como `estado`. Num projeto de dados do Brasil, "estado" é lido como unidade da federação (UF), e o nome confundia quem consulta. O arquivo guarda o que o landing não refaz: capturas (URL, hash, data), verificações, execuções e as chaves de identidade das pessoas.

## Decisão

1. O arquivo é `registry.duckdb` e o alias é `registry`. Os esquemas `metadata` e `identity` não mudam, e os nomes curtos (`metadata.capturas`) seguem resolvendo pelo `search_path` (`main,registry.metadata,registry.identity`).
2. O nome vem de uma constante (`REGISTRY_ALIAS` em `core/settings.py`); o perfil do dbt e o `scripts/servidor.sh` seguem o mesmo nome (`DADO_PUBLICO_REGISTRY_FILE`).
3. **Migração segura** (`migrations.adopt_registry`, na primeira abertura para escrita): se só o `estado.duckdb` existe, ele é renomeado (o `.wal` primeiro), sem copiar e sem apagar, e o log registra; se os dois existem, vale o `registry.duckdb`, o log avisa e o antigo não é tocado; se só o novo existe, nada a fazer. Nunca se cria um `registry.duckdb` vazio havendo `estado.duckdb`. O `scripts/servidor.sh dados` copia o nome novo e aceita o antigo.

## Alternativas consideradas

- `estado`: confunde com as UFs.
- `state`: ambíguo também em inglês (estado de máquina, estado do dlt/dbt).
- `registro`: o fundador achou pouco técnico.
- `ledger`: jargão contábil, pouco conhecido fora de finanças e blockchain.
- `provenance`: comprido e cobre mal a identidade.
- `control` e `audit`: não cobrem a identidade.
- `registry`: termo conhecido em TI (container registry, schema registry); é o registro durável do pipeline e das chaves de identidade. Escolha do fundador.

## Consequências

Quem consulta direto o arquivo troca `estado` por `registry` no `ATTACH`. Dado não muda de lugar nem é copiado. Implantação: parar o Dagster, copiar `estado.duckdb` como backup, subir a imagem, conferir as contagens.
