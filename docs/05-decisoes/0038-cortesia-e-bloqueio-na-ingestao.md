# ADR 0038: Cortesia em toda requisição, bloqueio sem insistência e partição mensal

- **Status:** aceito (2026-11-03, pelo fundador)
- **Data:** 2026-11-03
- **Complementa:** [ADR 0012](0012-dataset-por-item-lotes-com-envelope.md) (educação com a fonte, item 5).

## Contexto

O 0012 limitou a taxa só dos datasets por item. As fontes mensais de transparência do executivo são arquivos grandes atrás de proteções contra robôs: uma resposta "HTML de bloqueio" gravada como se fosse o arquivo poluiria o landing (imutável), e insistir agravaria o bloqueio.

## Decisão

1. **`access.rate_limit` (maior que zero) é o intervalo entre as requisições do download padrão** (HEAD e GET do arquivo), com relógio injetável nos testes. Não alcança `fetch.get` (datasets `foreach`, com intervalo próprio) nem módulos `custom/`.
2. **Bloqueio é erro, não retentativa:** no GET do download padrão, HTTP 403 ou 429, `Content-Type: text/html` (exceto quando o formato esperado é `html`) ou redirecionamento para fora do domínio registrável levantam `SourceBlocked` antes de gravar no landing. O plano registra a verificação `bloqueio` (erro, zerada com `ok` quando a fonte volta a responder) e interrompe o resto da fonte naquela execução; a próxima tentativa é a do agendamento seguinte. O **HEAD é brando**: sua falha só vira "sem informação". Não se contorna bloqueio.
3. **`partition: month` com `{month}` (AAAAMM) na URL.** O plano incremental pede o mês em curso e o anterior; um 404 do mês anterior não o marca como indisponível.

## Alternativas

- Backoff e nova tentativa no bloqueio: descartada, insistir é o que mais leva ao banimento.
- Cortesia só nos datasets por item (status quo): descartada, o risco maior está nos arquivos pesados.

## Consequências

Uma fonte bloqueada fica visível em `fontes_verificacoes` e no `observe`, sem dado errado no landing. Requisições a fontes custom (módulo `custom/`) seguem a regra do próprio módulo. O intervalo é por fonte e taxa, em memória, e **não é thread-safe** (um extrator por vez, como o resto do DuckDB). O domínio registrável usa uma lista curta de sufixos (`gov.br`, `leg.br`, `jus.br`...), sem dependência nova. Respostas 403 e 429 dos datasets por item continuam registradas como status do item (não interrompem o lote).
