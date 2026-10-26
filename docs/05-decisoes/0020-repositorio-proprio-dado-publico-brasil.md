# ADR 0020: Repositório próprio e nome dado-publico-brasil

- **Status:** aceito (2026-10-24, pelo fundador)
- **Data:** 2026-10-24
- **Substitui em parte:** o [ADR 0010](0010-duas-pastas-env-e-specs-fora.md) (duas pastas na mesma raiz) e o nome `plataforma-dados` dos ADRs anteriores.

## Contexto

A camada de dados e a aplicação *quem-decidiu* viviam em duas pastas do mesmo repositório, "até a criação de repositórios separados" (ADR 0010). A camada de dados serve qualquer aplicação, e não só a primeira.

## Decisão

1. **A camada de dados vive neste repositório**, `codigo-publico-brasil/dado-publico-brasil`, com o histórico da antiga pasta `plataforma-dados/`. O repositório `quem-decidiu` fica só com a aplicação, que lê apenas o esquema `marts`.
2. **Novos nomes:** pacote `dado_publico_brasil` (antes `plataforma_dados`), comando `dado-publico` (antes `plataforma`), variáveis `DADO_PUBLICO_*` (antes `PLATAFORMA_*`) e projeto dbt `dado_publico_brasil` (antes `quem_decidiu`).
3. **Pendências viram issues deste repositório**, não arquivos `.md`.
4. Os ADRs 0004 a 0010 mantêm os nomes antigos, porque registram a decisão da época.

## Consequências

- CI, modelos de issue e de pull request, `.gitignore` e `CLAUDE.md` passam a ser deste repositório.
- Quem tinha `.env` ou comandos com os nomes antigos precisa trocá-los.
- O warehouse local (`data_store/`) continua válido: os nomes de esquema não mudaram.
