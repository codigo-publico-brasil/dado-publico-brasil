# ADR 0010: Duas pastas no repositório, `.env` para conexões e specs fora

- **Status:** aceito (2026-10-21, pelo fundador)
- **Data:** 2026-10-21
- **Complementa:** [ADR 0009](0009-repositorio-de-dados-pacote-unico.md). Corrige o nome: o repositório e a distribuição são `plataforma-dados` (o import Python segue `plataforma_dados`, porque hífen não é válido em nomes de módulo).

## Decisão

1. **Duas pastas na raiz, projetos independentes**, até a criação de repositórios separados: `plataforma-dados/` (camada de dados) e `quem-decidiu/` (aplicação). Cada uma tem `pyproject.toml`, ambiente, testes, README, `AGENTS.md` e CI próprios (jobs `qualidade` e `qualidade-app`). A aplicação lê só o esquema `marts` e nunca importa a plataforma. Separar depois é mover a pasta.
2. **Conexões e segredos em variáveis de ambiente.** O modelo versionado é `.env.example`; o `.env` real fica fora do git (`.gitignore`), e o `gitleaks` roda no CI. Uso local: `uv run --env-file .env ...` (o `[tool.uv] env-file` do `pyproject` não é lido pelo `uv run`, então não é usado; o `dagster dev` carrega o `.env` da pasta sozinho). Em produção, a infraestrutura injeta as variáveis, de preferência de um gerenciador de segredos. Não há código para ler arquivo de configuração.
3. **Trilha de documentos e vetores fica para depois:** só o esqueleto `src/plataforma_dados/documents/` (docstring com as etapas e a regra de que o índice vetorial é derivado dos trechos relacionais), que já entra na matriz de imports (só importa `core`).
4. **Os specs (Spec Kit) saem dos repositórios** para a pasta `specs-legado/`, ao lado do repositório, porque mudaram muito com a nova arquitetura e serão refeitos. O histórico do git os preserva. As ferramentas do Spec Kit (`.specify/`, skills `speckit-*`) ficam na raiz por enquanto e apontam para um `specs/` que não existe até serem refeitos.
5. **Documentos:** `docs/` da plataforma guarda dados, domínio, engenharia, ADRs e planejamento histórico; `docs/` da aplicação guarda produto (contexto e metodologia).

## Consequências

- Comandos rodam a partir da pasta do projeto (`cd plataforma-dados && uv sync --all-extras`).
- `data_store/` fica em `plataforma-dados/data_store/` (fora do git); a aplicação o encontra por `QUEM_DECIDIU_WAREHOUSE`, com padrão `../plataforma-dados/data_store/warehouse.duckdb`.
- O pacote `quem_decidiu` da feature 001 (ambiente) vai com a aplicação.
- Pendente: renomear o repositório no GitHub e criar o repositório da aplicação; decidir o destino do `.specify/`.
