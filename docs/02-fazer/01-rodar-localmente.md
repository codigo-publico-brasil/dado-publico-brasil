# Rodar localmente

Para quem vai executar o pipeline na própria máquina. Responde: como subir o ambiente, rodar, consultar e abrir o PostgreSQL e o Dagster de desenvolvimento. Depois, os modos de execução (incremental, histórico, por item) e como consultar os dados. As camadas estão em [`03-camadas.md`](../01-entender/03-camadas.md).

Requisitos: Python 3.13 e [uv](https://docs.astral.sh/uv/). Na raiz do repositório (no Windows, se a política de aplicativos bloquear o comando `dado-publico`, troque `uv run dado-publico <comando>` por `uv run python -m dado_publico_brasil.orchestration <comando>`):

```bash
uv sync --all-extras
uv run dado-publico run --years 2025 2026
```

Outros modos: `--incremental` (a execução automática: só a partição em curso das fontes que declaram `schedule`) e `--historical --from-year 2000` (carga massiva). Os dados ficam em `data_store/` (fora do git).

**Conexões e segredos** vão em variáveis de ambiente: copie `.env.example` para `.env` (fora do git) e use `uv run --env-file .env dado-publico ...` (o `dagster dev` já carrega o `.env` da pasta). Em produção, a infraestrutura injeta as variáveis, de preferência a partir de um gerenciador de segredos.

```bash
uv run dado-publico query --sql "SELECT * FROM dim_pessoas_cadastro LIMIT 10"
uv run dado-publico docs      # grafo de linhagem e dicionário de colunas (dbt docs)
```

## PostgreSQL de serviço (o que as aplicações leem)

Requer Docker. Defina no `.env` `DADO_PUBLICO_PG_PASSWORD`, `DADO_PUBLICO_PG_LEITOR_PASSWORD` e `DADO_PUBLICO_POSTGRES_DSN` (modelo em `.env.example`) e, a partir da raiz:

```bash
docker compose up -d
uv run --env-file .env dado-publico publish
```

O `publish` copia todos os marts para o esquema `marts` do PostgreSQL numa troca atômica e dá leitura ao papel `leitor`. Os testes de integração rodam contra o banco `teste` (`DADO_PUBLICO_TEST_POSTGRES`); sem a variável, são pulados.

## Auditoria e datasets por item

```bash
uv run dado-publico verify
uv run dado-publico coverage
uv run dado-publico run --incremental --foreach 300
```

`verify` confere os hashes de todo o landing; `coverage` mostra o que já foi buscado nos datasets por item (tramitação, processos); `--foreach N` busca os N itens mais recentes que faltam (a carga total só quando pedida).

## Modos de execução

A pasta de armazenamento (`data_store/`, fora do git) vem de `DADO_PUBLICO_STORAGE_ROOT` (padrão `data_store`). Tudo a partir da raiz do repositório:

```bash
uv run dado-publico run --incremental                               # só a partição em curso (só as fontes com `schedule`)
uv run dado-publico run --historical --from-year 2000   # carga massiva
uv run dado-publico run --years 2024 2025 2026 --extra-years 2019   # anos escolhidos
uv run dado-publico run --incremental --source senado               # só uma fonte
uv run dado-publico run --incremental --foreach 300                 # + os 300 itens mais recentes que faltam nos datasets por item
```

- **Incremental:** datasets completos mais o ano corrente e o anterior (anos antigos são estáveis). Antes de baixar, pergunta-se à fonte (`ETag`, `Last-Modified`, tamanho) se o arquivo mudou; se não mudou, só se atualiza a data da última verificação. Se nada novo foi carregado, o dbt nem roda.
- **Histórico:** todos os anos do intervalo, para a primeira carga ou uma recarga.
- Etapas separadas: `extract`, `load [--rebuild]`, `transform` (dbt em duas fases, com a identidade no meio), `identity`, `publish`, `catalog`, `docs`, `query`, `observe`, `fotos`. Reparos sem baixar nada: `backfill`, `recheck`, `rebuild` (reconstrói o warehouse do landing). Verificação: `verify` e `coverage`. O `transform` mostra uma linha por modelo e por teste enquanto roda.
- **Datasets por item** (tramitação da Câmara, processo e detalhe do senador, detalhe das normas, vetos) só rodam com `--foreach N` ou `--foreach all`; a carga total é decisão de quem opera, por levar horas.
- **Auditoria:** `uv run dado-publico verify` (hashes do landing e das respostas) e `uv run dado-publico coverage` (o que já foi buscado e o que falta). Ver [auditoria](../02-fazer/05-auditar.md).
- **Dagster:** ver a seção seguinte.

## Dagster (interface, agendamento e linhagem)

O Dagster roda o pipeline sozinho: um agendamento por fonte (o cron `schedule` do YAML), a propagação automática do que depende do dado novo e o aviso de atraso. Detalhes em [`04-operar-e-publicar.md`](04-operar-e-publicar.md#dagster-o-pipeline-sozinho).

**Na sua máquina:**

1. Escolha uma pasta **absoluta** para o estado (por exemplo `data_store/.state/dagster`, fora do git), copie para ela o [`dagster.yaml`](../../dagster.yaml) (uma execução por vez) e defina `DAGSTER_HOME`, no `.env` ou no terminal.
2. A partir da raiz do repositório:

```bash
DAGSTER_HOME=<pasta absoluta> uv run dagster dev -m dado_publico_brasil.orchestration.definitions
```

3. Abra http://127.0.0.1:3000. Os agendamentos e sensores já sobem ligados; deixe o processo rodando. Na primeira vez, rode o job `atualizar_tudo` uma vez (o Dagster só propaga a partir do que ele mesmo já materializou).

**Em servidor (ou com Docker):** `docker compose --profile pipeline up -d --build` sobe o PostgreSQL e o Dagster, que reinicia sozinho e guarda o estado em um volume. O Docker Desktop precisa de pelo menos 8 GB de memória. Para rodar um passo isolado no container, recarregar uma captura e o que fazer quando algo trava (container que segura o warehouse, falta de memória, `publish` parado), veja [Operar e publicar](04-operar-e-publicar.md#rodar-por-partes-no-container).

Os passos rodam **em sequência** (o DuckDB em arquivo aceita um escritor por vez). Os datasets por item (`--foreach`) rodam pela linha de comando; o Dagster não os agenda.

## Como acessar os dados

O warehouse é `data_store/warehouse.duckdb`. Um arquivo DuckDB aceita um escritor por vez; com o pipeline parado, qualquer um dos três serve:

```bash
uv run dado-publico query --sql "SELECT * FROM dim_pessoas_cadastro WHERE nome_busca LIKE '%maria%'"
uv run python -c "import duckdb; print(duckdb.connect('data_store/warehouse.duckdb', read_only=True).sql('SELECT COUNT(*) FROM fct_votos'))"
```

O [catálogo](../03-consultar/01-catalogo.md) lista todas as tabelas, gerado do dbt (`uv run dado-publico catalog`).
