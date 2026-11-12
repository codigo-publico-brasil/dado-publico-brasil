# ADR 0052: versão citável do lake: publicação atômica, versão mensal imutável, `datapackage.json` e DOI só do manifesto

- **Status:** proposto (2026-11-11)
- **Data:** 2026-11-11
- **Altera:** [ADR 0035](0035-lakehouse-publico-no-r2.md) (item 8: a versão congelada deixa de ser "para quando alguém precisar" e passa a ser mensal; o caminho de toda noite continua) e [ADR 0055](0055-lake-como-unica-publicacao.md) (item 5: "sem versão por data"). Complementa o [ADR 0049](0049-licenca-apache-2-para-o-codigo-e-cc-by-para-os-dados.md) (como citar) e o [ADR 0047](0047-reconstrucao-incremental-e-export-por-particao.md) (o export continua escrevendo só o que mudou).
- **Para quem é:** quem publica o lake, quem o cita e quem o consome. Responde: o que um leitor vê durante o envio, como se cita um número de modo que ele se reproduza meses depois e o que (não) vai para o Zenodo.
- **Origem:** issue 274; referências: PUDL (build de toda noite e versão datada com DOI no [Zenodo](https://zenodo.org/communities/catalyst-cooperative)), [Our World in Data ETL](https://docs.owid.io/projects/etl/) (versão no caminho do dado) e o [Frictionless Data Package](https://datapackage.org).

## Contexto

O caminho do lake é sempre o dado atual, e o export gravava cada tabela **sobre** o arquivo publicado: durante o envio, o catálogo e o manifesto antigos apontavam para bytes novos (o SHA-256 não conferia) e conviviam anos de duas execuções. Também não há como citar "o que o lake dizia em outubro": o `id_execucao` identifica uma noite, mas os arquivos dela deixam de existir na noite seguinte.

## Decisão

1. **Cada execução grava em caminho próprio.** Tabela alterada vai para `<caminho>/<id_execucao>/<nome>.parquet` (ou `<caminho>/<id_execucao>/ano=AAAA/part-0.parquet`); o que o manifesto publicado aponta nunca é sobrescrito. Tabela sem mudança segue no arquivo de antes (o export continua barato, ADR 0047).
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
- O armazenamento passa a guardar, além do atual, os arquivos que cada versão mensal cita; um arquivo só sai quando nem o manifesto atual nem uma versão o cita. Não há expiração automática: reter ou retirar uma versão é decisão do fundador (por exemplo, para atender um titular), editando o manifesto da versão e anotando no changelog.
- Rodada que falha antes da troca pode deixar arquivos soltos em `<caminho>/<id>/`; `--prune` os limpa.
- Mudança de tipo de arquivo ou de layout fica registrada no manifesto; o consumidor continua lendo pelo catálogo ou pelo manifesto, nunca por caminho montado à mão.
