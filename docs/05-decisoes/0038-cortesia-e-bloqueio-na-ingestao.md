# ADR 0037: Cortesia em toda requisição, bloqueio sem insistência e partição mensal

- **Status:** aceito (2026-11-03, pelo fundador)
- **Data:** 2026-11-03
- **Complementa:** [ADR 0012](0012-dataset-por-item-lotes-com-envelope.md) (educação com a fonte, item 5).

## Contexto

O 0012 limitou a taxa só dos datasets por item. As fontes mensais de transparência do executivo são arquivos grandes atrás de proteções contra robôs: uma resposta "HTML de bloqueio" gravada como se fosse o arquivo poluiria o landing (imutável), e insistir agravaria o bloqueio.

## Decisão

1. **`access.rate_limit` vale para toda requisição da fonte** (HEAD, GET e arquivo), com relógio injetável nos testes.
2. **Bloqueio é erro, não retentativa:** HTTP 403 ou 429, `Content-Type: text/html` onde se espera arquivo ou redirecionamento para outro host levantam `SourceBlocked` antes de gravar no landing. O plano registra a verificação `bloqueio` (erro) e interrompe o resto da fonte naquela execução; a próxima tentativa é a do agendamento seguinte. Não se contorna bloqueio.
3. **`partition: month` com `{month}` (AAAAMM) na URL.** O plano incremental pede o mês em curso e o anterior; um 404 do mês anterior não o marca como indisponível.

## Alternativas

- Backoff e nova tentativa no bloqueio: descartada, insistir é o que mais leva ao banimento.
- Cortesia só nos datasets por item (status quo): descartada, o risco maior está nos arquivos pesados.

## Consequências

Uma fonte bloqueada fica visível em `fontes_verificacoes` e no `observe`, sem dado errado no landing. Requisições a fontes custom (módulo `custom/`) seguem a regra do próprio módulo. Respostas 403 e 429 dos datasets por item continuam registradas como status do item (não interrompem o lote).
