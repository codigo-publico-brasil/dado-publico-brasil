#!/usr/bin/env bash
# Falha se o diff do PR muda código/dado (src/, sources/, ddl/, dbt/) sem tocar a documentação
# (docs/, README.md, AGENTS.md) e sem a linha `Docs: não se aplica` no corpo do PR.
# Entrada: arquivos alterados em stdin (um por linha) e o corpo do PR em $PR_BODY (variável, nunca interpolado).
set -euo pipefail
arquivos=$(cat)
grep -qE '^(src|sources|ddl|dbt)/' <<<"$arquivos" || exit 0
grep -qE '^(docs/|README\.md$|AGENTS\.md$)' <<<"$arquivos" && exit 0
grep -qE '^Docs: não se aplica' <<<"${PR_BODY:-}" && exit 0
echo "::error::Este PR muda src/, sources/, ddl/ ou dbt/ e não toca em docs/, README.md nem AGENTS.md." >&2
echo "Faça uma destas: (1) atualize a documentação afetada (AGENTS.md, seção Documentação); ou (2) escreva no corpo do PR uma linha começando por 'Docs: não se aplica — <motivo>'." >&2
exit 1
