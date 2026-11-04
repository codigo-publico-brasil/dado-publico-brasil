# ADR 0043: Raw carregado em Parquet, substituição por partição e logs no Dagster

- **Status:** proposto (2026-11-04), para revisão do fundador
- **Data:** 2026-11-04
- **Altera:** o [ADR 0011](0011-buscar-ler-custom-e-chave-por-fonte.md) (a chave por fonte ganha a escrita `replace_partition`), o [ADR 0012](0012-dataset-por-item-lotes-com-envelope.md) (nada muda nos datasets por item, que seguem em `merge`) e o [ADR 0024](0024-regras-de-extracao-por-fonte.md) (a carga diária de arquivo anual completo deixa de somar versões). Complementa o [ADR 0042](0042-ciclo-noturno-de-processamento-e-publicacao.md) (o que se vê da captura e do ciclo na aba Runs). Relacionado: issues 154 (Parquet) e 155 (versões somadas).
- **Dependência nova:** `pyarrow` (extra `dlt[duckdb,parquet]`), que este ADR autoriza.

## Contexto

A reconstrução do raw de 28/10/2026 levou mais de seis horas, quase toda na votação do TSE. Três pontos distintos:

1. **Formato de carga.** O dlt grava no DuckDB por `insert_values` (`INSERT ... VALUES`, linha a linha).
2. **`merge` de arquivo anual completo.** `write: merge` compara cada linha nova com as da tabela (chave natural ou `_row_hash`). Num arquivo que é a foto completa de uma eleição, isso custa muito e ainda soma versões: o TSE republica o pacote do ano, as linhas que sumiram ficam no raw com o id da captura antiga e as que mudaram (chave por conteúdo) ficam duplicadas (issue 155; o aviso `linhas_removidas` só conta, não corrige). `replace` não serve: várias eleições vivem na mesma tabela.
3. **Pouca visibilidade.** A captura imprime algumas linhas e o resto (carga, dbt, identidade, export, docs) só mostra o fim; numa carga de uma hora não há sinal de vida.

**Medição** (máquina de desenvolvimento, Windows, DuckDB 2.0.0, dlt 1.31, `DADO_PUBLICO_DUCKDB_MEMORY=3GB`, warehouse temporário, mesmo código de leitura; script e dados fora do repositório):

| Votação do TSE | Linhas | `insert_values` + `merge` | Parquet + `merge` | Parquet + só acrescentar (`replace_partition`) |
| --- | --- | --- | --- | --- |
| 2016 (zip de 61 MB) | 943.082 | 1.062 s (17,7 min), pico 4,7 GB | 160 s, pico 1,55 GB | 192 s, pico 0,8 GB |
| 2026 (zip de 446 MB) | 6.748.427 | não terminou em 40 min (carga a 5% do tamanho final) | 1.701 s, pico 2,9 GB, warehouse 1,05 GB | 1.162 s, pico 1,55 GB, warehouse 0,46 GB |

- **Igualdade:** com o mesmo arquivo de 2016 (e, entre `merge` e só acrescentar, também com o de 2026, 6,7 milhões de linhas), as tabelas dos dois formatos têm o **mesmo esquema** (nomes, tipos e ordem das colunas, inclusive `_source_file_id` e `_ingested_at`), as mesmas contagens e a mesma soma de `hash(coluna)` e de não-nulos em **cada** coluna. Texto continua texto: o esquema é declarado em `columns` pelo contrato, então o Parquet não infere tipo nenhum nas colunas do raw.
- **Onde está o tempo:** com Parquet a carga em si deixa de dominar. Em 2026, de 28 min, cerca de 16 min são a leitura em Python (CSV dentro do zip, hash de cada linha, dicionário) e 9 min a conversão do dlt (normalize); o `COPY` do Parquet para o DuckDB é o resto. O ganho de 10 a 50 vezes que a issue previa não existe sobre a etapa de Python: o ganho medido é de cerca de 6,6 vezes no ano de 2016 (com um terço da memória) e, em 2026, o `insert_values` nem terminou onde o Parquet levou 28 min.
- **Memória e disco:** o pico em 2026 (2,9 GB) fica no limite de 3 GB do DuckDB mais o Python; no servidor (4 GB no container, disco lento) **não foi medido**. A pasta de estado do dlt (`.state/dlt`) fechou a carga com cerca de 0,7 GB para 6,7 milhões de linhas (pacotes concluídos do dlt, que ficam ali): conte com esse disco a mais durante a carga.
- Só acrescentar (sem comparar linha) não foi mais rápido que o `merge` em 2016 (192 s contra 160 s, dentro do ruído) e foi 32% mais rápido em 2026 (1.162 s contra 1.701 s), com metade da memória e do disco (o `merge` mantém um índice da chave: 1,05 GB contra 0,46 GB).

## Decisão

1. **Formato Parquet na carga do raw** (`loader_file_format="parquet"` no `run` do pipeline, em `ingestion/loader.py`), com `pyarrow` pelo extra `dlt[duckdb,parquet]`. Vale para todos os datasets (o teste de 2016, com igualdade coluna a coluna, e a suíte sintética da Câmara e do Senado, com tabelas filhas, passam sem mudar o esquema).
2. **Nova escrita declarativa `write: replace_partition`** no YAML da fonte, para o arquivo que é a **foto completa** de uma partição (o ano de uma eleição). A partição é **a própria captura**: depois de carregar a captura nova, saem do raw as linhas cujo `_source_file_id` pertence a **outras capturas da mesma fonte, dataset e URL**; antes da carga, saem as da própria captura (carga interrompida antes). O dlt recebe `append`.
   - **Não há coluna de partição nova.** `_source_file_id` já existe em toda linha, então o esquema e o teste `staging_sem_colunas_do_raw` não mudam, e a opção vale para qualquer fonte sem código por fonte.
   - **Idempotente:** recarregar a mesma captura não duplica. **Isolada:** nunca toca em linhas de outra URL (outro ano) nem de outro dataset; o raw espelha a versão atual do arquivo e o histórico fica no landing.
   - Não aceita `nested` (tabelas filhas). O aviso `linhas_removidas` não se aplica (as linhas antigas saem); o balanço da carga (`carga`) passa a informar quantas linhas de versões anteriores foram substituídas.
   - **Migração:** nenhuma para as tabelas existentes (todas as linhas já têm o id da captura). Na próxima captura nova de cada arquivo, as linhas das capturas antigas saem. O que o `merge` já somou de versões já descartadas pela troca de captura só sai com `load --rebuild --dataset <nome>`, que recarrega só a captura vigente de cada URL (o resultado é igual ao de `replace_partition`).
   - Aplicada aos seis datasets anuais completos do TSE: `candidaturas`, `bens`, `votacao`, `vagas`, `receitas_candidatos`, `despesas_candidatos`. Os datasets por item e por chave natural da Câmara, do Senado e das demais fontes seguem em `merge`.
3. **Logs no Dagster:** cada ativo (landing, raw, dbt antes e depois da identidade, identidade, export, docs) registra com `context.log` o início, o fim e a duração; o loader informa por dataset e por arquivo o tamanho, as linhas lidas e carregadas, as substituídas e um aviso de progresso a cada 30 segundos de leitura. O loader é agnóstico: recebe um chamador (`log`) e, sem ele, usa o `logging` padrão.

## Alternativas consideradas

- **Manter `insert_values`:** zero risco, mas as reconstruções ficam em horas e uma carga de 7 milhões de linhas não termina em tempo razoável.
- **Manter o `merge` em arquivo anual completo:** custa um índice e uma comparação por linha, e continua somando versões (issue 155). O `replace_partition` troca isso por dois `DELETE` por coluna indexada de inteiros.
- **`replace` total:** apaga as outras eleições da mesma tabela.
- **Estratégia `delete-insert` com `merge_key` do dlt** ([documentação](https://dlthub.com/docs/general-usage/merge-loading)): é o caminho idiomático do dlt para trocar uma partição, em uma só transação sobre a tabela de destino e a de staging. Não foi adotada porque (a) a `merge_key` apaga pelas linhas **que têm o mesmo valor de coluna**, e o valor da partição precisaria vir dos dados (o arquivo de uma eleição pode trazer um `ANO_ELEICAO` de outra, como as suplementares), então um ano poderia apagar linhas de outro; (b) exigiria uma coluna de partição nova no raw e um preenchimento retroativo de dezenas de milhões de linhas; (c) o dlt carrega os dados duas vezes (staging e destino) e, com `primary_key`, também compara linha a linha. A troca por captura usa o que o raw já tem. A contrapartida é que a troca acontece em dois comandos, e não em uma transação do dlt (o aviso fica no passo 2 acima: carga interrompida é refeita por inteiro).
- **`COPY`/`read_csv` do DuckDB direto, sem o dlt** (plano B da issue 154): mais rápido na leitura (elimina os 16 min de Python), mas é uma segunda forma de carga para manter, com `_row_hash`, balanço, rejeições, colunas de controle e evolução do esquema a reescrever. Fica como próximo passo **se** o tempo da leitura em Python continuar sendo o gargalo depois deste ADR; a medição acima mostra que é.
- **Coletor de progresso do dlt (`progress="log"`):** escreve no `logging` do processo, que o Dagster não mostra na aba Runs sem configuração extra e não cobre a leitura do CSV, que é onde está o tempo. Optou-se por um aviso próprio, enviado ao `context.log`.

## Consequências

- Dependência nova (`pyarrow`, cerca de 40 MB na imagem), autorizada aqui.
- A reconstrução do raw cai de horas para algo na ordem de uma hora para o TSE inteiro nesta máquina, **estimativa**: a medição é de dois arquivos, e o servidor (4 GB, disco lento) não foi testado. O gargalo restante é a leitura em Python.
- A tabela do raw dos datasets `replace_partition` não acumula mais versões: contagens e somas da votação, das receitas e das despesas podem **cair** em relação ao raw atual (que soma versões de 2022 e de 2026); conferir depois do `load --rebuild --dataset` comparando com a contagem de linhas do arquivo vigente.
- Os testes de dado do dbt sobre `_row_hash` continuam válidos (o hash segue na tabela).
- Os logs de captura longa ficam visíveis na aba Runs durante a execução, não só depois.
- Se a carga for interrompida entre a inserção e a retirada das versões antigas, o raw pode ter, por um instante, as duas versões; a captura não é marcada como carregada e a próxima execução a refaz.
