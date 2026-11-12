# ADR 0052: versão citável do lake: publicação atômica, versão mensal imutável, `datapackage.json` e DOI só do manifesto

- **Status:** aceito (2026-11-12), com a política de retenção abaixo
- **Data:** 2026-11-11
- **Altera:** [ADR 0035](0035-lakehouse-publico-no-r2.md) (item 8: a versão congelada deixa de ser "para quando alguém precisar" e passa a ser mensal; o caminho de toda noite continua) e [ADR 0055](0055-lake-como-unica-publicacao.md) (item 5: "sem versão por data"). Complementa o [ADR 0049](0049-licenca-apache-2-para-o-codigo-e-cc-by-para-os-dados.md) (como citar) e o [ADR 0047](0047-reconstrucao-incremental-e-export-por-particao.md) (o export continua escrevendo só o que mudou).
- **Para quem é:** quem publica o lake, quem o cita e quem o consome. Responde: o que um leitor vê durante o envio, como se cita um número de modo que ele se reproduza meses depois e o que (não) vai para o Zenodo.
- **Origem:** issue 274; referências: PUDL (build de toda noite e versão datada com DOI no [Zenodo](https://zenodo.org/communities/catalyst-cooperative)), [Our World in Data ETL](https://docs.owid.io/projects/etl/) (versão no caminho do dado) e o [Frictionless Data Package](https://datapackage.org).

## Contexto

O caminho do lake é sempre o dado atual, e o export gravava cada tabela **sobre** o arquivo publicado: durante o envio, o catálogo e o manifesto antigos apontavam para bytes novos (o SHA-256 não conferia) e conviviam anos de duas execuções. Também não há como citar "o que o lake dizia em outubro": o `id_execucao` identifica uma noite, mas os arquivos dela deixam de existir na noite seguinte.

## Decisão

1. **Cada execução grava em caminho próprio.** Tabela alterada vai para `<caminho>/<id_execucao>/<nome>.parquet` (ou `<caminho>/<id_execucao>/ano=AAAA/part-0.parquet`); o que o manifesto publicado aponta nunca é sobrescrito: o id tem resolução de segundo, e se ele já aparece em algum arquivo do manifesto publicado (duas execuções no mesmo segundo), ganha o sufixo `-2`, `-3`... (`<id>-2`). Tabela sem mudança segue no arquivo de antes (o export continua barato, ADR 0047).
2. **Publicação atômica por troca do ponteiro.** Catálogo e manifesto (e o `datapackage.json`) são trocados por último, depois de todos os arquivos; o `manifesto.json` é o último objeto gravado e o que o leitor lê primeiro. Os órfãos saem só depois da troca. Falha no meio deixa o publicado intacto e verificável; os arquivos soltos de uma execução que caiu saem na rodada seguinte que regravar a tabela ou com `--prune`.
3. **Versão datada mensal e imutável**, ao lado do caminho de toda noite: a primeira execução bem-sucedida de cada mês (UTC) fixa `versoes/AAAA-MM/` com `manifesto.json` (o publicado naquela hora, mais `versao`), `catalogo.duckdb` e `datapackage.json`. Depois de gravada, nunca é reescrita. Os Parquet **não são copiados**: a versão os referencia pelo caminho da execução, e o export não apaga arquivo citado por nenhuma versão. O custo é só o que mudou desde o mês anterior. O identificador citável é `AAAA-MM`.
4. **`datapackage.json` gerado do manifesto** ([Frictionless Data Package](https://datapackage.org)): um recurso por tabela, com URL, formato, esquema (tipo e descrição de cada coluna), licença da fonte e, nas tabelas de arquivo único, bytes e `sha256`. Não traz dado novo: tudo vem do manifesto. Existe na raiz (a noite) e em cada versão.
5. **DOI por versão, mas só do manifesto.** O depósito no Zenodo não se apaga, e este lake tem dado pessoal (ADR 0050). Deposita-se, por versão, o `manifesto.json` (com o SHA-256 de cada arquivo) e o `datapackage.json`; **nunca os Parquet**, que ficam no bucket. O número citado se verifica pelo hash, e um pedido de titular ainda pode ser atendido no bucket sem contrariar um depósito permanente. A conta e o primeiro depósito são do fundador, feitos à mão ([passo a passo](../02-fazer/04-operar-e-publicar.md#depositar-uma-versão-no-zenodo-fundador)); só se automatiza se a rotina se repetir.

## Alternativas consideradas

- **Copiar todos os Parquet para `versoes/AAAA-MM/`:** simples de entender, mas dobra o armazenamento a cada mês. Referenciar os arquivos da execução dá a mesma imutabilidade pelo custo do que mudou.
- **Gravar tudo de novo em caminho novo a cada noite:** atomicidade total sem lógica de órfãos, mas reenvia o lake inteiro todo dia e desfaz o ganho do ADR 0047.
- **Versão por tag de git ou por trimestre:** a mensal acompanha o ritmo das fontes e dá um identificador simples; trocar é mudar uma linha.
- **Depositar os Parquet no Zenodo (como o PUDL):** o PUDL não tem dado pessoal. Aqui, depósito permanente e pedido de titular são incompatíveis.
- **Versionar o bucket (versionamento de objetos do R2):** protege contra sobrescrita, mas não dá identificador citável nem manifesto por versão.

## Consequências

- Leitor com o catálogo da noite nunca vê bytes de duas execuções; a janela "anos de execuções diferentes" some.
- O armazenamento passa a guardar, além do atual, os arquivos que cada versão mensal cita; um arquivo só sai quando nem o manifesto atual nem uma versão retida o cita. A retenção é automática e limitada (seção abaixo); retirar uma versão antes disso (por exemplo, para atender um titular) é decisão do fundador.
- Rodada que falha antes da troca pode deixar arquivos soltos em `<caminho>/<id>/`; `--prune` os limpa.
- Mudança de tipo de arquivo ou de layout fica registrada no manifesto; o consumidor continua lendo pelo catálogo ou pelo manifesto, nunca por caminho montado à mão.

## Retenção e custo

Não dá para guardar cópias infinitas. Política (código em `lake.retention`, aplicada pelo `export` no passo dos órfãos):

1. **Retidos, com Parquet:** o que o manifesto raiz cita e as versões mensais dos últimos 12 meses (`DADO_PUBLICO_VERSOES_MESES`, padrão 12; a versão de 12 meses atrás ainda fica, a de 13 não).
2. **Fixada:** versão com `versoes/AAAA-MM/fixada.json` (DOI e data) mantém os Parquet para sempre, ou até pedido de remoção. O fundador a declara, depois de depositar no Zenodo, com `uv run dado-publico export --fixar AAAA-MM --doi 10.5281/...` ([passo a passo](../02-fazer/04-operar-e-publicar.md#depositar-uma-versão-no-zenodo-fundador)). Escolhido por ser um arquivo auditável no próprio bucket e um comando de poucas linhas; uma lista em configuração exigiria deploy a cada versão.
3. **Vencida** (mais de 12 meses e não fixada): perde só os Parquet que nenhuma versão retida nem o manifesto raiz cita. Mantém `manifesto.json`, `catalogo.duckdb` e `datapackage.json` (kilobytes); o manifesto ganha `arquivos_removidos` (data), de modo que a versão continua descrevendo e dando o hash, só que os dados não estão mais lá (o catálogo dela deixa de abrir as tabelas).
4. **Segurança da deleção:** é regra de órfãos, depois da troca do manifesto raiz; nunca apaga o que o raiz, uma versão fixada ou uma versão na janela cita. O marcador `arquivos_removidos` é gravado por último: se a execução cair antes, nada citado some e a rodada seguinte refaz.
5. **Pedido de titular (LGPD):** qualquer versão pode ser apagada à mão. O depósito no Zenodo leva só manifesto e `datapackage.json` (hashes), nunca Parquet, então o pedido pode ser atendido no bucket.

### Custo estimado

Preço oficial do R2 ([página consultada em 30/10/2026](https://developers.cloudflare.com/r2/pricing/)): Standard US$ 0,015 por GB-mês; saída de dados grátis; 10 GB-mês grátis; operações Class A US$ 4,50 e Class B US$ 0,36 por milhão. Infrequent Access (US$ 0,01 por GB-mês, mínimo de 30 dias, US$ 0,01 por GB recuperado) não compensa.

Tamanho medido no `manifesto.json` de 12/11/2026: **2,08 GB em 123 tabelas** (staging 1,51; marts 0,48; intermediate 0,09). Cerca de 1,64 GB são tabelas eleitorais, que só mudam em ano de eleição (só a votação do TSE tem 0,92 GB); cerca de 0,44 GB mudam durante o ano. **A fração que muda por mês é estimativa, não medida.**

Armazenamento = lake + 12 × mudança mensal × anos, sem política; com política = lake + 12 × mudança mensal + 1 versão fixada por ano (no máximo o lake). Custo mensal:

| Cenário | Horizonte | Sem política | Com política |
| --- | --- | --- | --- |
| Hoje, muda 0,44 GB/mês | 1 ano | 7,4 GB, US$ 0,00 (dentro dos 10 GB grátis) | igual |
| | 5 anos | 28,5 GB, US$ 0,28 | 17,8 GB, US$ 0,12 |
| | 10 anos | 54,9 GB, US$ 0,67 | 28,2 GB, US$ 0,27 |
| Pior caso, muda tudo (2,08 GB/mês) | 1 ano | 27 GB, US$ 0,26 | igual |
| | 5 anos | 127 GB, US$ 1,75 | 37 GB, US$ 0,41 |
| | 10 anos | 252 GB, US$ 3,63 | 48 GB, US$ 0,57 |
| Lake 10x (20,8 GB, muda 4,4 GB/mês) | 5 anos | 285 GB, US$ 4,12 | 178 GB, US$ 2,51 |
| | 10 anos | 549 GB, US$ 8,08 | 282 GB, US$ 4,07 |
| Lake 50x (104 GB, muda 22 GB/mês) | 5 anos | US$ 21 | US$ 13 |
| | 10 anos | US$ 41 | US$ 21 |

**Conclusão honesta:** no tamanho de hoje, até guardar tudo sem limite custa centavos a poucos dólares por mês; a política não é por dinheiro agora. Ela existe para o custo não crescer sem teto quando o lake crescer (dados novos de despesas e empenhos podem multiplicá-lo), para limitar o que precisa ser auditado e para facilitar a remoção por pedido de titular.

**Não medido:** o bucket privado (`cpb-interno`: cópias da identidade e do `metadata`) fica fora destas contas. **Revisar** a estimativa com o tamanho real depois do primeiro ano de versões mensais.
