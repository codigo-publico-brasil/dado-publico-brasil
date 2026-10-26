# Imagem do pipeline com o Dagster (ADR 0027): interface, agendamentos e propagação automática.
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --all-extras --no-dev --no-install-project
COPY . .
RUN uv sync --frozen --all-extras --no-dev && uv run dbt deps --project-dir dbt --profiles-dir dbt

ENV DAGSTER_HOME=/dagster_home
EXPOSE 3000
CMD ["uv", "run", "--no-sync", "dagster", "dev", "-h", "0.0.0.0", "-p", "3000", "-m", "dado_publico_brasil.orchestration.definitions"]
