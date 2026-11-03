# Imagem do pipeline com o Dagster (ADR 0027): interface, agendamentos e propagação automática.
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --all-extras --no-dev --no-install-project
COPY . .
RUN uv sync --frozen --all-extras --no-dev && uv run --no-sync dbt deps --project-dir dbt --profiles-dir dbt

# Na imagem não há `.git`: o CI passa o commit (`--build-arg GIT_SHA`) e `versao_commit` o registra.
ARG GIT_SHA=unknown
ENV DADO_PUBLICO_GIT_SHA=$GIT_SHA     PYTHONUNBUFFERED=1     DAGSTER_HOME=/dagster_home
EXPOSE 3000
# Serviço, não `dagster dev`: o compose sobe o `dagster-webserver` e o `dagster-daemon` (agendamentos e sensores),
# depois do serviço `init` (manifesto do dbt e `dagster.yaml`).
CMD ["uv", "run", "--no-sync", "dagster-webserver", "-h", "0.0.0.0", "-p", "3000", "-m", "dado_publico_brasil.orchestration.definitions"]
