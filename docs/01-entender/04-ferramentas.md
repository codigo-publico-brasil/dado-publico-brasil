# Ferramentas

Para quem vai rodar ou mexer no código. Responde: o que cada ferramenta faz aqui, por que foi escolhida e o que cada comando de verificação confere. Como as peças se encaixam: [`02-arquitetura.md`](02-arquitetura.md).

## No pipeline de dados

| Ferramenta | O que faz aqui | Ver |
| --- | --- | --- |
| **uv** | cria o ambiente e roda comandos (`uv sync`, `uv run`); o `uv.lock` fixa as versões | [docs.astral.sh/uv](https://docs.astral.sh/uv/) |
| **dlt** | carrega os arquivos do landing no raw, com `merge` idempotente | [ADR 0006](../05-decisoes/0006-adotar-dlt-dbt-e-dagster.md) |
| **dbt** | modelos SQL (staging, intermediate, marts), testes e documentação das colunas | [ADR 0006](../05-decisoes/0006-adotar-dlt-dbt-e-dagster.md) |
| **DuckDB** | o warehouse: um arquivo, sem servidor | [ADR 0014](../05-decisoes/0014-warehouse-lake-duckdb-e-postgres-de-servico.md) |
| **Dagster** | ordem das etapas, agendamento diário e grafo de linhagem | [ADR 0006](../05-decisoes/0006-adotar-dlt-dbt-e-dagster.md) |
| **PostgreSQL** (Docker) | banco de consumo que as aplicações leem; `docker compose up -d` sobe o de desenvolvimento | [ADR 0014](../05-decisoes/0014-warehouse-lake-duckdb-e-postgres-de-servico.md) |

## Verificação antes de um PR

```bash
uv sync --all-extras
uv run ruff check . && uv run ruff format --check . && uv run mypy && uv run pytest
```

| Comando | O que confere |
| --- | --- |
| `uv sync --all-extras` | instala o Python e todas as dependências de todos os motores, nas versões do `uv.lock` |
| `ruff check .` | **lint:** erros comuns, imports não usados ou fora de ordem, más práticas |
| `ruff format --check .` | **estilo:** o código está formatado como o `ruff format` formataria (só confere, não altera; para aplicar, rode sem `--check`) |
| `mypy` | **tipos:** as anotações de tipo (modo estrito) são coerentes entre si |
| `pytest` | **testes:** unidade, o pipeline sintético inteiro, contratos do repositório (nomes e descrições, catálogo em dia, fronteira entre os motores) |

Os testes são escritos a partir do critério de aceite, antes do código, e nunca são desativados para passar. A configuração de cada ferramenta está em `pyproject.toml`.
