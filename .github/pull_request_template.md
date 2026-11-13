## O que muda
Resumo curto e o item/issue relacionado.

## Autoria da IA
- O que a IA escreveu:
- O que uma pessoa revisou linha a linha:
- O que ficou incerto:

## Docs
<!-- Liste os documentos atualizados (docs/, README.md, AGENTS.md). Se o PR muda src/, sources/, ddl/ ou dbt/ sem documentação,
a esteira exige uma linha começando por "Docs: não se aplica — <motivo>" (sem os sinais de comentário). -->
Docs:

## Verificação
- [ ] Testes passam (inclusive os escritos antes do código)
- [ ] Nenhuma linha vermelha violada (ranking, recomendação de voto, linguagem avaliativa)
- [ ] Todo dado novo exibido tem fonte, URL e data de captura
- [ ] Documentação verificada contra o diff (AGENTS.md, seção Documentação) e `uv run pytest tests/test_docs_in_sync.py tests/test_docs_links.py`
- [ ] Nomes e descrições seguem `docs/03-consultar/02-convencao-de-nomes.md`
- [ ] Nenhuma dependência nova sem ADR
- [ ] Nenhum segredo ou dado pessoal no código
