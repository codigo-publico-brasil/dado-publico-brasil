# ADR 0059: `missing_status`, o 403 do host S3 é arquivo inexistente

- **Status:** proposto (2026-11-13)
- **Data:** 2026-11-13
- **Complementa:** [ADR 0045](0045-meses-fechados-405-e-pacote-unico.md) (403 só é "não publicado" no mês mais recente) e [ADR 0053](0053-nucleo-sem-nomes-de-fonte.md) (o núcleo não nomeia fonte).

## Contexto

O host de download do Portal da Transparência é o AmazonS3, que responde **HTTP 403** (e não 404) a um arquivo que não existe. Medido em 2026-11-13 (só leitura de status, sem baixar): `compras` existe de 202211 a 202607 e dá 403 em 202608, 202609 e 202610; `licitacoes` existe em 202211 e dá 403 de 202412 a 202610; `despesas-execucao/202610` existe. O portal publica `compras` com mais de um mês de atraso, então o mês 202609 dá 403 sem ser o mais recente do plano (202610). Pelo ADR 0045 isso é bloqueio: a execução interrompia a fonte antes dos meses antigos, que existem. Resultado em produção: 0 de 48 partições carregadas em `compras*` e `licitacoes*` e 2 de 48 em `despesas`, toda noite.

## Decisão

1. Chave opcional por dataset, `missing_status: [403]`: lista de códigos HTTP 4xx que o host devolve para arquivo inexistente (validada; 405 e 429 são recusados, continuam bloqueio).
2. Com a chave, o download que recebe esse código em **qualquer** mês registra `availability` com `tipo_ocorrencia = 'nao_publicado'` (sem `bloqueio`) e o plano segue. Sem a chave, nada muda (403 continua bloqueio, salvo o mês mais recente do ADR 0045).
3. O mês `nao_publicado` não vira "indisponível" (o arquivo pode sair): continua lacuna em `particoes` (aviso, não erro) e, na recuperação, vai **depois** dos meses nunca pedidos, para não ocupar as vagas do que existe.
4. `lag_months` e `first_month` do contrato não mudam: a fronteira real de publicação é desconhecida e o tratamento genérico a absorve.
5. `transparencia.yml` declara `missing_status: [403]` nos oito datasets mensais do host S3.

## Cortesia e carga

A recuperação segue o `rate_limit` do ADR 0038 (1 requisição a cada ~33 s na fonte) e o limite de 3 partições por dataset e por execução (`RECOVERY_LIMIT`), que não muda. Com compras (3 datasets, 1 zip) e licitações (4 datasets, 1 zip) cada um carrega 3 meses por noite (os irmãos reaproveitam o zip pelo HEAD), e despesas, 3: o backlog de 48 meses leva cerca de 16 noites por pacote. Nas primeiras noites os meses com 403 gastam vagas até serem vistos (em licitações, cerca de 8 noites a mais), depois passam ao fim da fila. `--historical` carrega tudo de uma vez quando a pessoa decidir.

## Alternativas

- Mudar `lag_months` por dataset: descartada, a defasagem real varia e é desconhecida.
- Tratar todo 403 como inexistente: descartada, esconderia bloqueio real em hosts que não são S3.

## Consequências

O backlog passa a andar toda noite. **Limite:** a chave não distingue um bloqueio real que use 403 no mesmo host; nesse caso o mês fica `nao_publicado` e a lacuna aparece em `particoes`, mas a fonte não para. Os 405 (verificação anti-robô do portal) continuam parando a fonte.
