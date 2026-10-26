# Como contribuir

Para quem quer corrigir, acrescentar ou melhorar algo. Responde: por onde começar, o que conferir antes do PR e o que nunca pode mudar.

1. **Comece por uma issue.** Descreva o problema ou a proposta. Mudança de arquitetura, estrutura, ferramenta ou dependência nova pede decisão antes (um [ADR](docs/05-decisoes/README.md)).
2. **Leia** o [`README.md`](README.md), o [mapa da documentação](docs/README.md) e as regras de dados do README. Elas não podem ser violadas.
3. **Prepare o ambiente e rode os checks:**
   ```bash
   uv sync --all-extras
   uv run ruff check . && uv run ruff format --check . && uv run mypy && uv run pytest
   ```
   O que cada comando confere está em [`docs/01-entender/04-ferramentas.md`](docs/01-entender/04-ferramentas.md).
4. **Escreva os testes primeiro**, a partir do critério de aceite, e não desative teste para passar.
5. **Um assunto por PR**, com a documentação atualizada no mesmo PR e o modelo de PR preenchido (inclusive "autoria da IA", se usou IA).
6. **Nomes e descrições** seguem a [convenção](docs/03-consultar/02-convencao-de-nomes.md). Para uma fonte nova, siga o [tutorial](docs/02-fazer/02-tutorial-nova-fonte.md).

Agentes de IA seguem também o [`AGENTS.md`](AGENTS.md). O merge é sempre de uma pessoa.
