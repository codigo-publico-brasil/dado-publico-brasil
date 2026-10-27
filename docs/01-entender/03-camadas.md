# Camadas do Dado Público Brasil

Como o dado percorre o projeto, da página oficial ao consumo, quais ferramentas fazem cada passo e onde mudar cada coisa. Serve também de material de estudo: os quadros **Conceito** nomeiam a prática de engenharia de dados por trás de cada decisão. Decisões formais: ADRs [0004](../05-decisoes/0004-camadas-da-plataforma-de-dados.md), [0005](../05-decisoes/0005-fontes-declarativas-e-portabilidade.md), [0006](../05-decisoes/0006-adotar-dlt-dbt-e-dagster.md), [0007](../05-decisoes/0007-dois-pacotes-e-camadas-de-mercado.md), [0008](../05-decisoes/0008-motores-separados-e-organizacao-por-poder-e-esfera.md) [0009](../05-decisoes/0009-repositorio-de-dados-pacote-unico.md), [0010](../05-decisoes/0010-duas-pastas-env-e-specs-fora.md) [0011](../05-decisoes/0011-buscar-ler-custom-e-chave-por-fonte.md) e [0012](../05-decisoes/0012-dataset-por-item-lotes-com-envelope.md).

## O desenho

```text
 FONTE OFICIAL      landing           raw_federal_camara   staging  →  intermediate  →  marts          aplicação
 (Câmara, Senado,   arquivos          tabelas fiéis       dbt: renomear,            dbt: entidades    (explorador,
  TSE, DOU...)  ──► intactos   ──►    à fonte        ──►  tipar, padronizar   ──►   joins,       ──► prontas p/      portal, API)
                    + hash            (dlt)               (1 modelo por tabela)     identidade       consumo, com
                                                                                     (Python)         contrato
 metadata: capturas, execuções, resultado dos testes do dbt    |   identity: chave própria de pessoa
 orchestration: Dagster (ordem, agendamento, linhagem)
```

| Camada | Pergunta que responde | Quem produz | Reconstruível? |
| --- | --- | --- | --- |
| **landing** | "O que a fonte entregou, exatamente?" | código próprio (pacote `ingestion`, `landing.py`) | não: é imutável |
| **raw** (`raw_<esfera>_<fonte>`) | "O que a fonte diz, tabela a tabela?" | **dlt**, guiado por `sources/<poder>/<esfera>/<fonte>.yml` | sim, a partir do landing |
| **staging** | "Como isso fica com nomes, tipos e caixa padronizados?" | **dbt** (views, um modelo por tabela do raw) | sim |
| **intermediate** | "Como juntar e re-granular para chegar às entidades?" | **dbt** (tabelas, uma finalidade por modelo) | sim |
| **core** | "Quais são os catálogos que dão chave a tudo (pessoas, territórios, cargos, partidos, eleições, disputas, tipos de evento)?" | **dbt** (tabelas e seeds curados, com contrato de colunas) | sim |
| **marts** | "Como entregar cada entidade pronta para consumo?" | **dbt** (tabelas, com contrato de colunas) | sim |
| **identity** | "Quem é cada pessoa, em todas as fontes?" | código próprio (pacote `transformation`, `identity.py`) | não: a chave não se reaproveita |
| **metadata** | "O que rodou, quando, com que resultado?" | código próprio e dbt | não |

> **Conceito: arquitetura em camadas (medalhão).** *Bronze, prata e ouro* do mercado correspondem aqui a raw, staging/intermediate e marts. Cada camada tem uma responsabilidade, só depende da anterior e pode ser refeita a partir dela.

> **Conceito: ELT e raw fiel.** Guarda-se o dado como veio e transforma-se depois, dentro do banco, em SQL. O raw só tem as colunas permitidas pelo contrato (assim o CPF nunca entra), sem renomear nem limpar. Se uma regra estava errada, corrige-se o SQL e refaz-se, sem baixar tudo de novo.

## Mapa de schemas do warehouse

Um único arquivo DuckDB, um schema por camada. Lista completa do que existe, e por quê:

| Schema | Papel | Quem cria | Segue o padrão de... |
| --- | --- | --- | --- |
| `raw_federal_camara` | tabelas fiéis à fonte, uma por dataset | dlt | dlt: um schema (dataset) por fonte; `raw_` diz a camada e `federal` a esfera |
| `dlt_tmp_raw_federal_camara` | área temporária do dlt para fazer `merge` e `replace`; não é camada, ninguém lê | dlt | dlt cria `<dataset>_staging`; renomeamos (`staging_dataset_name_layout`) para não parecer a camada `staging` do dbt |
| `staging` | views, uma por tabela do raw, com nomes, tipos e caixa padronizados | dbt | guia da dbt Labs |
| `intermediate` | tabelas de passagem (re-granularidade e junções) | dbt | guia da dbt Labs |
| `core` | catálogos de referência do modelo de dados ([ADR 0030](../05-decisoes/0030-modelo-de-dados-pessoa-no-centro.md)); em construção, junto com `fatos`, `analise` e `servico` | dbt | modelo-alvo em [`08-modelo-de-dados.html`](08-modelo-de-dados.html) |
| `marts` | entidades prontas, com contrato; **o que a aplicação lê** | dbt | guia da dbt Labs |
| `identity` | chave própria de pessoa e tabela de ligação | código próprio | específico do projeto (não se reconstrói) |
| `metadata` | execuções, capturas, resultado dos testes, migrações | código próprio e dbt | específico do projeto |
| `main` | schema padrão do DuckDB; fica vazio | DuckDB | padrão do DuckDB |

O dbt, por padrão, grava em `<schema do perfil>_<schema do modelo>`; aqui a macro `generate_schema_name` usa só o nome do schema do modelo, o que é permitido e recomendado quando cada ambiente tem o seu banco. As tabelas `_dlt_loads`, `_dlt_pipeline_state` e `_dlt_version` dentro de `raw_federal_camara` são controle do dlt.

## Por que `identity` e `metadata`

As outras camadas guardam o **dado da fonte** em estágios de tratamento. Estas duas guardam o que o projeto **acrescenta**:

- **`identity` (identidade):** a chave própria `id_pessoa`, que liga a mesma pessoa em fontes diferentes (um deputado na Câmara, candidato no TSE). É a única camada que **não se reconstrói** do landing: uma chave já entregue a uma aplicação não pode mudar, então ela nasce por código com migração e ganha cópia imutável a cada execução. Detalhes em [`05-identidade-de-pessoas.md`](05-identidade-de-pessoas.md).
- **`metadata` (metadados):** dados *sobre* o pipeline, não sobre o poder público: cada captura (URL, hash, data, caminho do arquivo), cada execução (versão do código, linhas, resultado), o resultado dos testes do dbt e as verificações das fontes. É o que torna o dado **auditável**: toda linha do raw aponta para `metadata.captures`. O nome segue o uso do mercado ("metadata" = dado que descreve dado). As aplicações leem os marts e, para a página de qualidade, `metadata.captures`, `metadata.dbt_results` e `metadata.source_checks`.

## Descrições e dicionário de colunas

Cada tabela e coluna dos marts é descrita **uma vez**, no YAML do dbt (`_legislativo__models.yml`). Daí saem:

- o [catálogo e o dicionário de colunas](../03-consultar/01-catalogo.md), gerados por `uv run dado-publico catalog`;
- os comentários gravados no próprio banco (`persist_docs`), visíveis em `duckdb_tables()` e `duckdb_columns()` e em ferramentas como o DBeaver;
- o site navegável do dbt, com o **grafo de linhagem**: `uv run dado-publico docs` (abre em http://127.0.0.1:8080; pipeline parado).

Um teste falha se alguma coluna dos marts ficar sem descrição.

## Poder, esfera e fonte

O projeto vai capturar dados dos três poderes (legislativo, executivo, judiciário) e das três esferas (federal, estadual, municipal); hoje só existe o legislativo federal. A regra de organização:

| Eixo | Onde aparece |
| --- | --- |
| poder | pasta `sources/<poder>/...` e campo `power` da declaração |
| esfera | pasta `sources/<poder>/<esfera>/...`, campo `level` e o nome do schema `raw_<esfera>_<fonte>` |
| fonte | nome do arquivo da declaração, prefixo `stg_<fonte>__` e a coluna `fonte` dos marts |

Os marts são **por entidade** (`pessoas`, `proposicoes`, `votacoes`...), não por fonte, para que Câmara e Senado sejam consultados juntos. Para fonte nova: declaração em `sources/`, modelos de staging e, se for entidade nova, um mart (ver [especificação de fonte](../02-fazer/03-especificacao-de-fonte.md)).

## Como a captura é flexível

Três passos por dataset ([ADR 0011](../05-decisoes/0011-buscar-ler-custom-e-chave-por-fonte.md)): **buscar** (`ingestion/fetch.py`: HTTP com nova tentativa, cabeçalhos e credenciais por variável de ambiente), **guardar** (`landing.py`: arquivo com hash e registro da captura, igual para toda fonte) e **ler** (`read.py`: CSV e JSON). Uma fonte que precise de outro jeito (SOAP, robô, pacote compactado) tem um módulo em `ingestion/custom/<poder>/<esfera>/<fonte>.py` que substitui só o passo necessário; a saída de `buscar` é sempre um arquivo com hash, então o resto não muda. Passo a passo em [especificação de fonte](../02-fazer/03-especificacao-de-fonte.md).

**Quando cada fonte é capturada.** Cada fonte declara `schedule` no YAML (um cron, fuso America/Sao_Paulo). O Dagster cria um agendamento por fonte e, a cada execução, captura só a partição em curso (o ano ou o mês corrente); antes de baixar, pergunta à fonte (`ETag`, `Last-Modified`, tamanho) se o arquivo mudou. Sem `schedule`, a fonte só roda quando alguém pede. Quando o raw recebe dado novo, o que depende dele (dbt, identidade, publicação no PostgreSQL) roda sozinho; sem dado novo, nada a jusante roda. Detalhes e como ver o que está atrasado: [`04-operar-e-publicar.md`](../02-fazer/04-operar-e-publicar.md#como-saber-o-que-está-desatualizado) e [ADR 0027](../05-decisoes/0027-orquestracao-automatica-por-fonte.md).

## O dbt seguindo as práticas da dbt Labs

O projeto segue o guia oficial de estrutura (“How we structure our dbt projects”):

- **staging**: um modelo por tabela do raw, `stg_<fonte>__<entidades>`, **views**, só renomear, converter tipos e padronizar texto. Sem joins nem agregações. É o único lugar que usa `source()`.
- **intermediate**: uma finalidade por modelo (`int_..._agregados`, `..._ligados_a_...`, `..._unidos`), **tabelas** fora dos marts. Aqui estão a re-granularidade e os joins.
- **marts**: **entidades** com nome simples e plural (`pessoas`, `proposicoes`, `votacoes_votos`), um grain por tabela, largos, com **contrato de colunas e tipos** (`contract.enforced`). Declarados como *exposure* para a aplicação.
- **YAML** ao lado dos modelos (`_<pasta>__models.yml`, `_<fonte>__sources.yml`), com descrição, `meta` (sensibilidade, grain, dono) e testes de chave (`unique`, `not_null`, `relationships`).
- **Testes**: genéricos no YAML, singulares em `tests/`. As lacunas conhecidas da fonte são testes `severity: warn` (a contagem de linhas que falharam mede a lacuna); reconciliações e integridade são `error` e interrompem o pipeline. O resultado de cada execução vai para `metadata.dbt_results`.
- **Frescor** declarado nas fontes (`freshness` e `loaded_at_field`), medido com `dbt source freshness`.
- **Funções de texto** como macros nativas do DuckDB (`proper_name`, `sentence_case`, `standardize_summary`), criadas no `on-run-start`; SQL puro, sem código Python por linha.
- **Duas fases**: o dbt roda em duas passadas, separadas por tag, porque a identidade (código Python) fica no meio: primeiro `staging` e os modelos `pre_identity`; depois a resolução de identidade; depois o resto.

> **Conceito: contrato de dados.** Um contrato declara colunas e tipos que o produtor garante ao consumidor. Se o SQL do mart mudar de forma incompatível, o `dbt build` falha em vez de entregar dado quebrado à aplicação.

## Propriedades que o pipeline garante

**Idempotência.** Rodar duas vezes dá o mesmo resultado: o dlt grava por `merge` na chave natural; o dbt recria as tabelas; a identidade só cria a pessoa que ainda não existe. Testes rodam o pipeline sintético inteiro.

**Imutabilidade do landing.** O arquivo é salvo com o hash no nome e nunca é sobrescrito. Se a fonte mudar o conteúdo, nasce um segundo arquivo.

**Organização do landing.** O caminho diz a origem, a referência e a data da extração: `landing/<fonte>/<dataset>/<referência>/<AAAAMMDD>/<nome>-<hash>.<ext>`. A referência é o ano, o mês (`AAAAMM`, no DOU) ou a legislatura do arquivo, ou `completo` quando o dataset não é particionado (lotes de datasets por item também ficam em `completo`). A data é a da captura. Capturar de novo o mesmo conteúdo em outro dia não cria arquivo: vale o primeiro e só a data da última verificação muda ([ADR 0021](../05-decisoes/0021-landing-por-fonte-dataset-e-data.md)).

**Linhagem.** Toda linha do raw leva `_ingested_at` (quando chegou) e `_source_file_id`, que aponta para `metadata.captures` (URL, hash, tamanho, datas, caminho); nos datasets por item, `metadata.capture_items` aponta para cada resposta dentro do lote. Cada execução registra a versão do código (commit). O dlt grava `_dlt_load_id` por carga e o Dagster mostra o grafo entre ativos.

> **Conceito: linhagem de dados.** O rastro de cada dado até a origem. Exigência do projeto: "todo dado exibido precisa de fonte oficial, URL e data de captura".

**Reprodutibilidade.** Raw, staging, intermediate e marts se refazem do landing: `load --rebuild`, depois `transform`. Só `identity` (a chave própria) não se reconstrói, e por isso é criada por migração.

**Evolução do esquema.** Coluna nova no contrato: o dlt a acrescenta sozinho. Coluna removida: `load --rebuild`. Nos marts, mudança incompatível quebra o contrato do dbt.

## Armazenamento

Um único arquivo DuckDB, com um esquema por camada (`raw_<esfera>_<fonte>`, `staging`, `intermediate`, `marts`, `identity`, `metadata`). Limite do DuckDB em arquivo: um processo escritor por vez. Por isso o dbt roda em outro processo, com a conexão do chamador fechada, e a aplicação abre em modo somente leitura. 

**PostgreSQL de serviço** ([ADR 0014](../05-decisoes/0014-warehouse-lake-duckdb-e-postgres-de-servico.md)). O dbt roda só no DuckDB; o PostgreSQL só recebe os marts já prontos, pelo comando `publish`: as tabelas vão para um esquema de trabalho (`marts_novo`) e são trocadas por `marts` num único comando atômico, então quem lê vê os marts antigos ou os novos, nunca metade. Depois da troca o comando confere que cada tabela chegou com as mesmas linhas. O papel `leitor` (somente leitura) é criado pela infraestrutura (em desenvolvimento, por `docker/postgres-init.sh`); o código nunca cria papéis. Ainda não há índices: entram quando uma aplicação declarar como consulta cada mart. A extensão `postgres` do DuckDB é baixada na primeira execução (precisa de rede).

**Cópia imutável da identidade.** A chave `id_pessoa` não pode mudar depois de entregue a uma aplicação, e reconstruir a partir do landing não garante as mesmas chaves. Cada execução da identidade grava `snapshots/identity/<data-hora>/` (um Parquet por tabela de `identity`) dentro da pasta de armazenamento; nunca se sobrescreve. `dado-publico verify` confere se a cópia mais recente é igual à identidade do warehouse.

## Caixa dos textos

A fonte traz nomes e ementas ora em maiúsculas, ora em minúsculas. A regra única, em `macros/text_functions.sql`:

- Só se altera texto **100% maiúsculo ou 100% minúsculo**; com as duas caixas, fica como está.
- **Nomes:** `REGINALDO LÁZARO DE OLIVEIRA LOPES` vira `Reginaldo Lázaro de Oliveira Lopes`. Partículas (`da`, `de`, `dos`) em minúsculas; algarismos romanos e siglas sem vogal (`JHC`) em maiúsculas.
- **Rótulos** (tipo de autor, situação): caixa de frase.
- **Ementas:** o texto oficial vai em `ementa_oficial` e a versão padronizada em `ementa`. As siglas que a fonte escreve em maiúsculas dentro de outras ementas (`BNDES`) são mantidas (modelo `int_ementas_siglas_extraidas`).
- O que a regra não resolve fica visível no teste `pessoas_com_nome_em_maiusculas`.

Reescrever ementa em linguagem simples com IA **não** é padronização; se vier a existir, será campo derivado à parte, rotulado como gerado por IA (ver [governança](06-governanca.md)).
