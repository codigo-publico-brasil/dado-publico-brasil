# ADR 0041: meses fechados, 405 como bloqueio e um download por pacote

- **Status:** aceito (2026-11-03, pelo fundador)
- **Data:** 2026-11-03
- **Complementa:** [ADR 0038 (cortesia)](0038-cortesia-e-bloqueio-na-ingestao.md).

## Contexto

No primeiro backfill de despesas e contratos do Portal da Transparência, os 12 primeiros meses vieram e os seguintes responderam HTTP 405. O pipeline tratou o 405 como "indisponível" e seguiu pedindo (cerca de 135 requisições inúteis). Além disso, o portal publica o mês só depois de fechado, e três datasets (contratos, itens e aditivos) baixavam o mesmo zip três vezes.

## Decisão

1. **405 é bloqueio**, junto de 403 e 429 (GET do download padrão): `SourceBlocked`, a fonte para naquela execução. O HEAD continua brando.
2. **`lag_months: N` (só `partition: month`)** declara que o dataset só tem meses fechados: o mês "em curso" do plano é o de N meses atrás (`lag_months: 1` pede até o mês anterior). Um **403 no arquivo do mês mais recente** de um dataset mensal é "ainda não publicado" (verificação `availability` com esse texto, sem bloqueio, e o resto da fonte segue); em mês mais antigo, 403 segue sendo bloqueio.
3. **Um download por pacote:** datasets cuja URL difere só no fragmento `#` leem o mesmo arquivo. Se outro dataset da fonte já capturou aquele arquivo na mesma partição e o HEAD informa que não mudou (`ETag`, ou `Last-Modified` e tamanho), a captura é anotada apontando para o mesmo arquivo do landing, sem novo GET. Vale também para as emendas.

## Alternativas

- Tratar 405 só nos datasets mensais: descartada, o código de status não depende do dataset.
- Um dataset único com os quatro CSVs do zip: descartada, mudaria o modelo do raw (uma tabela por CSV é a regra).

## Consequências

Menos requisições e menos risco de bloqueio. A captura de um dataset irmão ainda custa um HEAD (com o intervalo do ADR 0038). Se o HEAD falhar, o zip é baixado de novo.
