# Rodar localmente

Para quem vai executar o pipeline na própria máquina. Responde: como subir o ambiente, rodar, consultar e abrir o PostgreSQL e o Dagster de desenvolvimento. Os modos de execução (incremental, histórico, por item) estão em [`../01-entender/03-camadas.md`](../01-entender/03-camadas.md#como-executar).

Requisitos: Python 3.13 e [uv](https://docs.astral.sh/uv/). Na raiz do repositório:

```bash
uv sync --all-extras
uv run dado-publico run --years 2025 2026
```

Outros modos: `--incremental` (a execução diária: só a partição em curso dos datasets que cada fonte declara como `refresh: daily`) e `--historical --from-year 2000` (carga massiva). Os dados ficam em `data_store/` (fora do git).

**Conexões e segredos** vão em variáveis de ambiente: copie `.env.example` para `.env` (fora do git) e use `uv run --env-file .env dado-publico ...` (o `dagster dev` já carrega o `.env` da pasta). Em produção, a infraestrutura injeta as variáveis, de preferência a partir de um gerenciador de segredos.

```bash
uv run dado-publico query --sql "SELECT * FROM marts.pessoas LIMIT 10"
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

## Dagster

Guarde o estado dele em uma pasta absoluta, por exemplo `data_store/.state/dagster`, em `DAGSTER_HOME`:

```bash
uv run dagster dev -m dado_publico_brasil.orchestration.definitions
```
