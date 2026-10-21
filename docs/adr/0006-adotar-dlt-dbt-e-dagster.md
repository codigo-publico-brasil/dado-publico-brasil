# ADR 0006: Adotar dlt, dbt-core e Dagster (open source) no lugar do motor próprio

- **Status:** aceito (2026-10-20, pelo fundador). A estrutura de pastas, os nomes das camadas e a limpeza de texto foram revistos pelo [ADR 0007](0007-dois-pacotes-e-camadas-de-mercado.md); a escolha das ferramentas continua valendo.
- **Data:** 2026-10-20
- **Substitui em parte:** [ADR 0005](0005-fontes-declarativas-e-portabilidade.md) (motor próprio de carga e de SQL, camada própria sobre SQLAlchemy). Mantém dele: especificação declarativa por fonte, configuração central, extração histórica e incremental, e a separação entre declaração e código.
- **Depende de:** [ADR 0002](0002-pilha-tecnologica.md) (já aceitou Dagster e dbt-core), [ADR 0004](0004-camadas-da-plataforma-de-dados.md) (camadas)
- **Regra do fundador:** só software livre. Nada de recurso pago.

## Contexto

O ADR 0005 propôs um motor próprio (leitura de YAML, DDL, upsert, evolução de esquema, SQL por tabela, pipeline). O fundador perguntou se algo pronto serve. Uma pesquisa (ADR 0005, seção de referências) e um **spike com dados reais** (esta data, descartado depois) responderam que sim, para quase tudo que o motor próprio faz.

### O que o spike mostrou

Ambiente isolado, fora do repositório, com arquivos reais da Câmara já capturados:

| Peça | Resultado |
| --- | --- |
| **dlt** (carga) | 7.889 deputados e 61.536 proposições carregados em DuckDB (2 s e 11 a 13 s). Rodar de novo não duplicou (`merge` por chave). **Coluna nova no código apareceu na tabela sozinha**, sem DDL. Cada carga gravou um identificador (`_dlt_load_id`) que liga a linha à execução. Regras de texto próprias (`nome_proprio`, `ementa`) funcionaram dentro do recurso. |
| **dbt-core** + dbt-duckdb (SQL e testes) | Dois modelos de serviço (`pessoa`, `proposicao`) e seis testes (`unique`, `not_null`) em 0,5 s, declarados em YAML. As fontes do dbt apontam para as tabelas do dlt. |
| **Dagster** (orquestração) | Um job executou dlt e depois dbt na ordem certa, com **linhagem entre ativos** (`padronizado_deputados` para `servico/pessoa`) e um agendamento diário (cron) declarado. A dependência veio do `sources.yml` do dbt por um tradutor de poucas linhas. |

### O que o spike revelou de problema

- **DuckDB é um arquivo de um só processo.** Uma etapa que ainda segura o arquivo impede outra de ler; no PostgreSQL do piloto isso some. Localmente, cada etapa precisa fechar a conexão.
- **O dlt guarda o estado do pipeline em `~/.dlt/`**, inclusive o destino. Reusar o nome de um pipeline com outro caminho de arquivo grava no caminho antigo (aconteceu no spike). Precisa fixar a pasta de estado dentro de `dados/`.
- **`row_number()` no dbt não serve de chave de pessoa:** a chave muda quando os dados mudam. A chave própria de pessoa e a ponte de identificadores continuam **tabela persistente**, mantida por código, como no ADR 0004.
- **O YAML declarativo do dlt (`dlt.yml`) é recurso pago** (dltHub). Não será usado. O dlt livre se configura em Python.
- **Muitas dependências** (cerca de cem pacotes transitivos). No Windows, um caminho de pasta muito longo quebrou a importação de uma biblioteca (`sqlglot`); resolvido com caminho curto.
- Nada disso foi medido em volume completo (1,4 milhão de linhas) nem com a interface do Dagster.

## Decisão

Usar, todos livres (Apache 2.0, confirmado em pesquisa para dlt, dbt-core e Dagster; DuckDB é MIT, não confirmado em pesquisa):

| Papel | Ferramenta | Substitui |
| --- | --- | --- |
| Carga e esquema (do bruto para o padronizado) | **dlt** | `armazenamento.py`, `esquema.py` (sincronizar), `motor.py`, upsert, evolução de esquema, estado da extração incremental |
| Transformação (integrado e servico) e testes de dados | **dbt-core** (SQL e YAML) | `sql.py`, os arquivos `.sql` com executor próprio, `modelo.yml` de integrado e servico, parte de `verificacoes.py` |
| Orquestração, agendamento e linhagem | **Dagster** (open source) com dagster-dbt e dagster-dlt | `pipeline.py`, `__main__.py` e o `pipeline.yml` proposto |
| Banco local | **DuckDB** (um arquivo); **PostgreSQL** no piloto | SQLite |

Continua **código próprio**, pequeno e testado, porque é regra do projeto e não existe pronto:

- **Bruto imutável:** download com hash no nome, `controle.captura`, pergunta condicional à fonte (`ETag`/`Last-Modified`), nunca sobrescrever.
- **Regras de texto** (`nome_proprio`, `rotulo`, `ementa`) e a leitura sem CPF/RG (lista de colunas permitidas; o recurso do dlt só emite o que está na especificação).
- **Identidade de pessoas:** chave própria, ponte `pessoa_identificador`, regra de ligação conservadora, mandatos.
- **Testes de dados específicos** que o dbt não cobre (reconciliação com totais da fonte, linhas perdidas entre camadas): viram testes singulares do dbt (SQL) onde possível.

### Declaração e código separados

```text
declaracoes/                    # só YAML e SQL
  configuracao.yml              # pasta, banco, agendamento
  fontes/camara.yml             # URL, formato, conjuntos, colunas e regras (esta é a nossa camada fina)
  dbt/                          # projeto dbt: models/ (SQL), sources.yml, schema.yml (testes)
src/quem_decidiu/dados/         # só código
  bruto/                        # download, hash, captura, condicional
  fontes/camara/                # fábrica de recursos dlt a partir de camara.yml; ganchos
  identidade/                   # pessoa, ponte de identificadores, mandato
  orquestracao/                 # definições do Dagster (ativos, agendamentos)
```

A **camada fina própria** é uma função que lê `declaracoes/fontes/camara.yml` e devolve recursos do dlt (mapeamento de colunas, regras, chave, tipo). É o mesmo padrão do dlt-meta e do Airbyte (manifesto lido por motor), com poucas linhas, porque o trabalho pesado (esquema, merge, destino, estado) fica com o dlt.

### Extração histórica e incremental

- **Histórico (massivo):** `dagster job execute` (ou a interface) com a configuração `anos: 2001..2026` na declaração; o Dagster pode usar **partições anuais** para recargas parciais.
- **Incremental:** agendamento diário que processa as partições "não estáveis" (ano corrente e anterior) e os conjuntos completos; o dlt faz `merge` e o bruto pula o que a fonte diz que não mudou.
- A diferença entre os dois modos passa a ser **configuração das partições**, não código.

### Spark

Fora do escopo agora (volume de 1,4 milhão de linhas). O dbt tem adaptador para Spark e o dlt tem destinos de data lake; a troca futura é de banco e adaptador, não de arquitetura.

## Dependências novas (exigem aprovação, conforme o AGENTS.md)

`dlt` (com `duckdb`), `dbt-core`, `dbt-duckdb`, `duckdb`, `dagster`, `dagster-dbt`, `dagster-dlt`, `dagster-webserver`. Saem: `sqlalchemy` e `pyyaml` deixam de ser necessários se a camada fina usar o `pyyaml` que o dlt e o dbt já trazem (a decidir na implementação). Dagster+ (nuvem), dbt Cloud e dltHub não são usados.

## Alternativas consideradas

- **Terminar o motor próprio do ADR 0005:** funciona (73 testes passando), mas repete o que as três ferramentas fazem melhor (esquema, estado, linhagem, agendamento, testes de dados) e é código a manter para sempre. Mantém menos dependências.
- **Airbyte ou Meltano:** exigem servidor ou conectores Singer; mais infraestrutura do que o volume pede.
- **Só dbt e cron:** mais simples, mas sem linhagem, partições nem interface.
- **dlt YAML (`dlt.yml`):** pago; descartado pela regra do fundador.

## Consequências

- A refatoração do ADR 0005 em andamento é substituída: os arquivos `.sql` e o `fonte.yml` viram, quase sem mudança, modelos do dbt e a declaração da fonte; `armazenamento`, `esquema`, `motor`, `extracao` (parte de estado) e `pipeline` próprios saem.
- Mais peças para aprender e operar (três ferramentas), o que também é o objetivo de estudo do projeto.
- O banco local passa de SQLite para DuckDB; a integração entre camadas por `ATTACH` do SQLite dá lugar a esquemas num mesmo arquivo DuckDB, o que simplifica as consultas.
- Antes de aceitar: repetir o spike com o volume completo e conferir a interface do Dagster.

## Como ficou implementado (2026-10-20)

- **Um arquivo DuckDB** (`dados/quem_decidiu.duckdb`) com os esquemas `controle`, `padronizado`, `integrado` e `servico`. O dlt grava o padronizado (estado do dlt em `dados/.dlt`, não em `~/.dlt`); o dbt grava o integrado e o servico; o código próprio grava o controle e a identidade.
- **O dbt roda em outro processo** (`python -c "from dbt.cli.main import cli"`), porque o arquivo DuckDB aceita um escritor por vez e o dbt-duckdb mantém o arquivo aberto dentro do processo. O chamador fecha a conexão antes; a execução é registrada depois (`execucao.registrar_externa`).
- **Declarações em `declaracoes/`:** `configuracao.yml`, `fontes/camara.yml` (o antigo `fonte.yml`), `dbt/` (os antigos arquivos `.sql` viraram modelos; `modelo.yml` virou `schema.yml`), `migracoes/` (controle e identidade) e `catalogo/`. O código em `src/quem_decidiu/dados/`.
- **Camada fina própria** (`nucleo/carga.py`): monta as linhas do YAML (origem, regra, tipo, chave, deduplicação) e entrega ao dlt com dicas de coluna, para a tabela existir mesmo sem valores.
- **Sem SQLAlchemy:** não foi necessário; as dependências aprovadas são `pyyaml`, `duckdb`, `dlt[duckdb]`, `dbt-core`, `dbt-duckdb`, `dagster`, `dagster-dbt`, `dagster-dlt` e `dagster-webserver`.
- **Dagster** (`orquestracao/definicoes.py`): ativos `bruto_camara`, `padronizado_camara`, `identidade_camara`, os modelos do dbt e `verificacoes_de_dados`, com agendamento diário incremental. A interface não foi aberta nem testada nesta data; a definição foi carregada e a linhagem validada no spike.
