# ADR 0051: Raw em Parquet por captura e estado em arquivo próprio

- **Status:** proposto (decisão do fundador de 2026-11-11: todo o raw em Parquet; detalhes para aceite)
- **Data:** 2026-11-11
- **Altera:** o [ADR 0014](0014-warehouse-lake-duckdb-e-postgres-de-servico.md) (itens 2 e 4: o raw sai do arquivo DuckDB e a identidade passa a morar em `estado.duckdb`) e o [ADR 0043](0043-raw-em-parquet-substituicao-por-particao-e-logs.md) (a carga continua Parquet, mas o Parquet deixa de ser etapa e vira o destino; `replace_partition` vira remoção de pasta). Complementa o [ADR 0036](0036-r2-privado-fonte-da-verdade-do-que-nao-se-reconstroi.md) (item 1: a cópia de trabalho da identidade e do metadata muda de arquivo; a fonte da verdade no bucket privado não muda).
- **Para quem é:** quem opera ou implementa a plataforma. Responde: onde mora o raw, o que o `warehouse.duckdb` ainda guarda e o que se prova antes de migrar.
- **Origem:** estudo de viabilidade medido em 11/11/2026 (issues 212 e 269).

## Contexto

Um único `warehouse.duckdb` serializa `load`, `transform` e `export`: o DuckDB admite um escritor por vez ([concorrência](https://duckdb.org/docs/2.0/connect/concurrency.html)), então uma carga longa bloqueia as demais etapas. O raw é reproduzível do landing (ADR 0014, item 2 do ADR 0036) e não precisa de banco: precisa de um lugar barato de escrever e ler. O estado que não se reproduz (`metadata`, `identity`) tem outra natureza e outro ritmo.

## Decisão

1. **O loader grava cada captura com o destino `filesystem` do dlt** ([documentação](https://dlthub.com/docs/dlt-ecosystem/destinations/filesystem)): escrita `append`, formato [Parquet](https://dlthub.com/docs/dlt-ecosystem/file-formats/parquet), compressão zstd (`NORMALIZE__DATA_WRITER__COMPRESSION=zstd`), em `<storage>/raw/<esquema>/<tabela>/<id_captura>/`. As tabelas filhas (`nested`) seguem a mesma regra.
2. **A pasta do raw contém só as capturas vigentes.** Depois da carga, saem as pastas das capturas substituídas da mesma URL; no início do `load_pending`, sai o que não está em `landing.current_captures`. Substitui a remoção por `DELETE` do `replace_partition` (ADR 0043, item 2), que passa a ser o comportamento de todo dataset.
3. **As tabelas `raw_<esfera>_<fonte>.<tabela>` viram views geradas do YAML** (genéricas, sem nome de fonte): `read_parquet(..., union_by_name=true)` ([leitura de Parquet](https://duckdb.org/docs/2.0/data/parquet/overview.html)). Nos datasets `merge` (chave natural), a view usa `QUALIFY row_number() OVER (PARTITION BY chave ORDER BY _source_file_id DESC) = 1`, e as filhas entram por semi-join no pai ([comportamento do `merge` no dlt](https://dlthub.com/docs/general-usage/merge-loading)). Dataset sem captura vira view vazia, tipada pelo contrato.
4. **Chave natural repetida no mesmo arquivo fica na primeira ocorrência**, e a colisão continua contada (`conflicting`).
5. **`metadata` e `identity` vão para `estado.duckdb`**, anexado em leitura ao warehouse do dbt, que guarda só o que o dbt produz. O `estado.duckdb` continua com um escritor (o lock fica restrito a ele).

## Alternativas consideradas

- **`COPY` próprio do DuckDB:** reescreveria as tabelas filhas, o `_row_hash` e o balanço que o dlt já entrega (mesma razão do ADR 0043 para ficar no dlt).
- **Vigência por manifesto Parquet:** segunda fonte da verdade, pode divergir de `landing.current_captures`. Descartada: a pasta já é a vigência.
- **`ATTACH` do `estado.duckdb` em leitura por outro processo:** medido, com um escritor aberto o `ATTACH READ_ONLY` de outro processo falha por lock, o que devolveria o lock ao raw. Por isso o anexo é do próprio processo do dbt, e o escritor do estado é o mesmo fluxo que já era único.
- **Híbrido da issue 212, opção 1 (raw em `.duckdb` por fonte):** menos mudança, mas mantém um escritor por arquivo e o `ensure_tables`. Fica como **reversão** (gatilhos abaixo).
- **Delta Lake / delta-rs:** transação e vigência nativas, mas dependência nova; exige ADR próprio e só se justifica se a vigência por pasta falhar.

## Consequências

- **Raw sempre igual a uma recarga do landing.** No `merge`, a linha que a fonte removeu sai do raw (hoje fica até `--rebuild`); o aviso `linhas_removidas` continua, medido antes de apagar a pasta antiga.
- Somem `ensure_tables`, `backfill_ingested_at` e a área temporária do `merge`. As tabelas filhas perdem `_dlt_root_id` (nenhum modelo dbt o usa).
- **Migração única** por `load --rebuild`, que coincide com a recarga do hash novo (issue 269), feita pelo fundador no servidor.
- **Custo medido** em 10 milhões de linhas num container Linux (dlt 1.31.0, DuckDB 2.0.0, pyarrow 26.0.1, 4 threads, 3 GB): leitura de 1,1 a 2 vezes a tabela nativa; deduplicação cerca de 10% mais lenta; `union_by_name` cerca de 20%; carga de 1 milhão de linhas em 56,2 s contra 54,9 s; disco de 318 MB contra 456 MB.
- **Sem compactação agora**; gatilho: dataset acima de ~10 mil arquivos ou bind da view acima de 2 s.
- **Não verificado:** se o `COMMENT` de view e de coluna sobrevive a `CREATE OR REPLACE VIEW` (o catálogo e o `describe` dependem disso); conferir no PR de implementação.

## Plano de PRs

1. **`estado.duckdb`** para `metadata` e `identity`, provando contagem e soma de hash por tabela de staging e marts iguais às de `main` no pipeline sintético, e `id_pessoa` idêntico.
2. **Raw em Parquet e views**, provando igualdade no sintético e, em storage isolado, view contra a tabela antiga em três datasets reais (um `replace_partition`, um `foreach`/`merge`, um com filhas), explicando as diferenças que forem só histórico do `merge`.
3. **Compactação**, só se o gatilho disparar.

## Gatilhos de reversão (cair para o híbrido)

- A prova de igualdade falhar por motivo fora da mudança de semântica documentada acima.
- `transform` completo mais de 30% mais lento que hoje.
- Pico de memória acima de 4 GB na deduplicação.
- Bind de view acima de 2 s.
