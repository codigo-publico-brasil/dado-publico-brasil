# ADR 0035: Lakehouse público no R2, em Parquet, com caminho estável

- **Status:** proposto (2026-11-02)
- **Data:** 2026-11-02
- **Altera:** [ADR 0014](0014-warehouse-lake-duckdb-e-postgres-de-servico.md) (item 1 e gatilho 6a) e [ADR 0033](0033-marts-com-a-terminologia-da-dbt-labs.md) (a camada publicada no lake passa a incluir staging e intermediate; o PostgreSQL continua recebendo só os marts).
- **Complementa:** [ADR 0034](0034-manter-duckdb-e-postgres.md) (DuckDB calcula e PostgreSQL serve; sem DuckLake).

## Contexto

O objetivo do projeto é um lakehouse público que qualquer pessoa consulte e audite. Hoje o único artefato é um `warehouse.duckdb` de 11 GB: um arquivo, um escritor, sem partição, que só existe na máquina do mantenedor. O ADR 0014 previa exportar para Parquet apenas ao passar de 300 GB ou 6 h; mas publicar deixou de ser questão de escala e virou requisito de produto.

Tudo de `raw` a `marts` é reconstruível do landing ([ADR 0004](0004-camadas-da-plataforma-de-dados.md)). O que não se reconstrói é o landing, a identidade e os metadados de captura. Pesquisa de formatos (nov/2026): o R2 Data Catalog (Iceberg) exige token de API até para leitura, o que impede acesso anônimo; o DuckLake 1.0 exige DuckDB ≥ 1.5.2 para ler, não tem chave primária e não confirma suporte do dbt.

## Decisão

1. **O DuckDB é só motor de cálculo descartável.** O dado público é Parquet no Cloudflare R2, atrás de domínio próprio (`datalake.codigopublicobrasil.com.br`), com cache da Cloudflare.
2. **Camadas publicadas:** `staging` (a base tratada de cada fonte: todos os campos da fonte, nomes e tipos padronizados, colunas de auditoria), `intermediate`, `marts` e `metadata.capturas` (URL, hash SHA-256 e data de cada captura). `raw` não é publicado (o staging cobre o mesmo conteúdo, padronizado). Um teste exige que o staging exponha todas as colunas do raw.
3. **Colunas de auditoria padronizadas:** o staging acrescenta `fonte`, `id_captura`, `dt_captura`, `url_fonte` e `sha256_captura` por uma macro única; intermediate e marts propagam `fonte`, `id_captura` e `dt_captura`. Teste no dbt e em `tests/test_names_and_descriptions.py`.
4. **Caminho estável, sem pasta por versão, organizado como o resto do projeto:** `staging/<poder>/<esfera>/<fonte>/<modelo>` (a árvore de `sources/`, [ADR 0008](0008-motores-separados-e-organizacao-por-poder-e-esfera.md); a pasta sai do nome da fonte no modelo, sem declaração nova), `intermediate/<modelo>` (plano), `marts/<domínio>/<tabela>` (a pasta de domínio do dbt; as views `app_` não vão) e `metadata/capturas`. Tabela pequena é um arquivo `.parquet`; a grande é `<tabela>/ano=AAAA/part-0.parquet`. Parquet em ZSTD, arquivos de ~128 MB a 1 GB, metadado com execução, versão do código e data.
   - **Partição declarada no dbt, ao lado do modelo:** `config.meta.particao`, uma expressão SQL que dá o ano (ex.: `year(dt_eleicao)`); vira a coluna `ano` no caminho. O `export` lê do `manifest.json` do dbt e registra a coluna no manifesto público. Só reparte se a tabela tem `particao` e passa de um tamanho mínimo medido; abaixo disso, um arquivo ordenado pelo período. Teste do dbt exige que a expressão nunca seja nula. Nunca por dia.
   - **Vocabulário:** os nomes são os da dbt Labs (`staging`, `intermediate`, `marts`; `dim_`, `fct_` de Kimball). Para quem vem do lake, a equivalência com o medalhão (bronze = landing e raw, prata = staging e intermediate, ouro = marts) está em `docs/03-consultar/06-consumir-o-lake.md` e no `manifesto.json`.
5. **Porta de entrada:** `catalogo.duckdb` (uma view por tabela com a lista explícita de arquivos, `COMMENT` de tabela e coluna, `id_execucao`) e `manifesto.json` (arquivo, linhas, bytes, SHA-256, esquema, descrição). Bucket público não lista, por isso o catálogo enumera os arquivos.
6. **Publicação só depois dos testes do dbt, subindo apenas o que mudou** (hash contra o manifesto anterior) e trocando manifesto e catálogo por último.
7. **Cópia privada do que não se reconstrói:** snapshots da identidade e metadados, em bucket privado, com teste de restauração; o mecanismo está no [ADR 0036](0036-r2-privado-fonte-da-verdade-do-que-nao-se-reconstroi.md). O landing (que guarda CPF e outros campos que o raw descarta) é **nunca público**; por ora fica só no disco local, com as fotos (risco aceito no 0036).
8. **Histórico sem duplicar:** "como estava em tal data" vem do landing privado e de `id_captura`/`dt_captura`. Release congelada (`releases/AAAA-MM/`, só marts) fica para quando alguém precisar citar uma versão fixa, com expiração por regra do R2.
9. **Sem dependência nova:** o `httpfs` do DuckDB escreve no R2 com segredo S3 vindo de variável de ambiente. A cópia de arquivos brutos fica na operação, fora das dependências Python.

## Alternativas consideradas

- **Pasta por execução (`v=<execução>`):** história completa, mas duplica o dado a cada rodada e estoura o armazenamento.
- **Iceberg no R2 Data Catalog:** padrão de mercado, mas exige token mesmo para ler.
- **DuckLake:** bom para escrita incremental e versões; aqui os marts são recriados por inteiro, a identidade precisa de chave primária e o dbt não está confirmado.
- **Só marts no lake:** menor, mas esconde a base tratada de cada fonte, que é o que permite auditar a derivação.
- **Manter o arquivo DuckDB como único artefato:** frágil, sem partição e inacessível ao público.

## Consequências

- Um novo passo (`export`) entre `transform` e `publish`; depende de segredo do R2.
- O tamanho do lake público e o custo (R2 cobra cerca de US$ 0,015 por GB-mês acima dos 10 GB gratuitos; sem custo de saída) só se conhecem após a primeira exportação, que registra a medida.
- Há uma janela curta de inconsistência nas tabelas particionadas durante o envio; fica documentada.
- **Gatilhos para reabrir o formato de tabela:** carga incremental dos marts, tabela acima de 100 GB ou consumidores pedindo Iceberg (os mesmos Parquet podem ser registrados depois).
- Staging, hoje view, passa a ser exportado: exige as colunas de auditoria e o teste de cobertura do raw antes da primeira publicação.
