# ADR 0061: Cache negativo na recuperação e uma pergunta por arquivo por execução

- **Status:** proposto
- **Data:** 2026-11-16
- **Complementa:** [ADR 0038](0038-cortesia-e-bloqueio-na-ingestao.md) (cortesia) e [ADR 0059](0059-missing-status-host-s3.md) (`missing_status`).
- **Para quem é:** quem opera a captura. Responde: por que a captura noturna deixou de sondar meses que ainda não existem, e o que continua sondado.

## Contexto

Com `missing_status` (ADR 0059) o 403 do S3 é arquivo inexistente e a recuperação segue. Medido em produção (14 a 16/11/2026): `captura_transparencia` passou de 4-8 min para 42-44 min por noite. Cada mês inexistente custa um HEAD e um GET recusados, ambos a 1 requisição a cada ~33 s (`rate_limit`), e se repete por dataset: oito datasets leem só dois pacotes. Os meses sem arquivo (`licitacoes` tem 16 a 20) ocupam as vagas de `RECOVERY_LIMIT` e voltam a ser sondados toda noite.

## Decisão

1. **Cache negativo:** na recuperação (`plan_recovery`), uma partição de dataset com `missing_status` cujo arquivo (URL sem o `#`) teve como última verificação `availability` um `nao_publicado` há menos de `NEGATIVE_CACHE_DAYS` (7, constante em `landing.py`) não é sondada. Passado o prazo, volta ao plano. O mês em curso e o anterior ficam de fora do cache (o plano normal os pede toda noite). Pedido explícito (`--historical`, `--years`) não passa pela recuperação e ignora o cache.
2. **Uma pergunta por arquivo e execução:** `extract_plan` guarda o resultado do HEAD e a recusa do GET por URL sem o `#`; os datasets irmãos do mesmo pacote reaproveitam, sem requisição nem espera. Cada dataset segue registrando a sua verificação em `metadata.fontes_verificacoes`.
3. `RECOVERY_LIMIT`, `rate_limit` e o que carrega por noite para os meses que existem não mudam; as vagas que os meses em cache liberam vão aos meses ainda não vistos.

## Alternativas

- Chave no contrato para o prazo: descartada por ora (uma constante basta; vira chave se uma fonte pedir outro prazo).
- Cache entre execuções do HEAD de meses que existem: descartada, o `unchanged` já poupa o download e a mudança de arquivo precisa ser vista.

## Consequências

Um mês que o portal publica durante o prazo é visto em até 7 dias (ou na hora, pelo plano normal, se for o mês em curso ou o anterior, ou com `--years`). A verificação `nao_publicado` de cada dataset passa a aparecer só uma vez por prazo e partição, não toda noite: a contagem de ocorrências diminui sem que o dado mude.
