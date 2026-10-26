# ADR 0021: Landing por fonte, dataset, referência e data

- **Status:** aceito (2026-10-24, pelo fundador)
- **Data:** 2026-10-24

## Contexto

O landing guardava todos os arquivos de uma fonte numa pasta só (`landing/camara/` tinha 223 arquivos misturados). A origem e a data da extração só apareciam em `metadata.captures`, e o DOU, que é por mês, não mostrava o mês no caminho.

## Decisão

1. **Caminho:** `landing/<fonte>/<dataset>/<referência>/<AAAAMMDD>/<nome>-<hash>.<ext>`. A referência é a partição do dataset (ano, mês `AAAAMM` ou legislatura) ou `completo`; a data é a da captura, em UTC.
2. **Mesmo conteúdo, outro dia:** não grava outro arquivo. Fica o primeiro, e `metadata.captures` registra a data da última verificação.
3. **Os arquivos existentes foram migrados** em 24/10/2026 (570 arquivos) só mudando de pasta e atualizando `metadata.captures.path`; conteúdo e hash não mudaram, e `dado-publico verify` confere todos.
4. **`metadata.captures.path` continua a fonte da verdade** do caminho; nada lê o caminho por convenção.

## Consequências

- Achar um arquivo por origem, referência ou data não exige consultar o banco; copiar ou aplicar retenção por prefixo (por exemplo, para armazenamento de objetos) fica direto.
- Um `manifesto.csv` de um motor antigo, sem captura registrada, continua em `landing/camara/` (não é lido por nada).
