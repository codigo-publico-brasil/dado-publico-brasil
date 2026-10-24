# ADR 0019: Diário Oficial da União só no landing, por mês, nos últimos 3 meses

- **Status:** aceito (2026-10-24, pelo fundador)
- **Data:** 2026-10-24
- **Complementa:** o [ADR 0016](0016-bens-votos-e-emendas.md), item 8, que deixou o DOU de fora.

## Contexto

A Imprensa Nacional publica o DOU em XML, em zips mensais por seção (S01 atos normativos, S02 pessoal, S03 contratos e avisos), sob licença CC BY-ND 3.0 (sem derivações). O fundador quer guardar os arquivos agora e, depois, usar busca semântica (RAG) sobre o texto em vez de transformá-lo em tabelas. O INLABS (acesso por credencial) está em manutenção e o dados.gov.br respondeu 401.

## Decisão

1. **Só o landing:** o zip original, sem alteração, com hash, URL e data de captura. Sem tabela no raw nem modelo no dbt (`raw: false` no dataset). Guardar e ler o arquivo é livre; o que a licença restringe é redistribuir trecho modificado, e nada disso é publicado.
2. **Fonte própria** `executivo/federal/dou`, com três datasets (`secao1`, `secao2`, `secao3`), partição por **mês** (`partition: month`, valor `AAAAMM`) e `first_month` para limitar o histórico. Por ora, de agosto de 2026 em diante (3 meses, 9 zips, 620 MB).
3. **Download por HTTP simples:** a página do mês (`?ano=2026&mes=Outubro`) traz os links dos zips no HTML, e o robô não precisa de navegador. O pedido precisa de `Accept: */*`; o `User-Agent` continua identificando o projeto.
4. **Fora do plano incremental diário:** o zip do mês corrente é reescrito todo dia (o nome traz `_AtualizadoHHMMSS`) e cada versão ocuparia centenas de MB; o mês entra só quando pedido (`plataforma extract --source dou --years 2026`).
5. **Uso futuro (RAG):** índice privado do texto, sempre com o link da fonte e a data; resposta gerada por IA é rotulada como tal. O XML aberto não substitui a versão certificada (PDF).

## Alternativas consideradas

- **Playwright:** desnecessário, os links estão no HTML.
- **Tabelas a partir do XML:** pode contar como derivação (CC BY-ND) e perde o texto; o RAG preserva o documento.
- **Entrar no incremental diário:** acumularia gigabytes por mês de arquivos quase iguais.

## Consequências

- O landing cresce 620 MB para 3 meses; o histórico de 2026 inteiro seria cerca de 4,1 GB.
- Cada mês fechado tem um arquivo estável; o mês corrente precisa ser recapturado quando se quiser a versão final.
- Para trazer mais meses, baixa-se o `first_month` no YAML.
