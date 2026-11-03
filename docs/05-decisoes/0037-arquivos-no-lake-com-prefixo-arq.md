# ADR 0037: Arquivos no lake público, com prefixo `arq_` e tabela de controle

- **Status:** proposto (2026-11-03); aprovado pelo fundador
- **Data:** 2026-11-03
- **Altera:** [ADR 0035](0035-lakehouse-publico-no-r2.md) (item 7: o landing deixa de ser "nunca público") e [ADR 0036](0036-r2-privado-fonte-da-verdade-do-que-nao-se-reconstroi.md) (as fotos passam do disco local ao R2).

## Contexto

O lake publica tabelas. O projeto também guarda arquivos que não são tabelas e que o público deve poder baixar: o Diário Oficial da União (zips mensais, [ADR 0019](0019-dou-so-no-landing.md), licença que permite redistribuir o original sem modificação) e as fotos oficiais dos candidatos (50 mil imagens extraídas dos pacotes do TSE, 1 GB). O fundador exige um único bucket e a mesma árvore, sem pasta de topo nova, e que se veja de relance o que é arquivo e o que é tabela. O landing do TSE guarda campos pessoais que o raw descarta e continua fora do lake.

## Decisão

1. **Mesma árvore das tabelas:** o arquivo mora na camada de onde saiu, em `staging/<poder>/<esfera>/<fonte>/`, ao lado das tabelas da fonte.
2. **Prefixo `arq_`:** pasta cujo nome começa com `arq_` é uma coleção de arquivos. Todo o resto do lake é tabela (Parquet). O prefixo segue o dos `dim_`, `fct_` e `brg_`.
3. **Tabela de controle ao lado:** cada coleção tem `arq_<nome>.parquet`, com a lista de seus arquivos. Segue a convenção de nomes e descrições, entra no `catalogo.duckdb` e no `manifesto.json` como qualquer tabela e leva as colunas de auditoria (`fonte`, `id_captura`, `dt_captura`, `url_fonte`, `sha256_captura`). Colunas próprias: `caminho` (relativo à pasta da coleção), `sha256_arquivo`, `qtd_bytes`, `content_type` e `fl_original` (verdadeiro quando os bytes são idênticos ao capturado, como o zip do DOU; falso quando foram extraídos ou renomeados, como as fotos).
4. **Declarativo e agnóstico a fonte:** o dataset ganha o bloco `arquivos: {colecao, caminho, membro?, publicar?}` no YAML da fonte. Sem `membro`, o arquivo capturado é a própria coleção (DOU, `fl_original` verdadeiro); com `membro` (regex), extraem-se os arquivos do zip (fotos, `fl_original` falso) e o zip não sobe. `publicar` é falso por padrão: sem `publicar: true` o arquivo fica só no disco local (landing do TSE, com CPF). Nenhum comando, ativo ou função do núcleo nomeia fonte ou tipo de arquivo (AGENTS.md). O DOU sobe sem modificação e com atribuição à Imprensa Nacional na página do lake. A proveniência de cada arquivo materializado fica em `metadata.arquivos`.
5. **Caminhos estáveis, sem pasta por versão.** Exemplos: `staging/judiciario/federal/tse/arq_fotos/<ano>/<UF>/<sq_candidato>.<ext>`; `staging/executivo/federal/dou/arq_secoes/<seção>/<AAAAMM>/<arquivo>.zip`. `foto_caminho` do `fct_candidaturas` aponta para esse caminho.
6. **Envio:** só o que falta ou mudou (SHA-256 contra o controle), com `x-amz-checksum-sha256`, `Content-Type` correto e `Cache-Control: immutable` para fotos. Sem dependência nova (o assinador SigV4 do `export`).
7. **Teste de consistência** (`export --verificar`): todo objeto de uma pasta `arq_` está no controle, e todo arquivo do controle existe com o mesmo hash.

## Alternativas consideradas

- **Pasta de topo `arquivos`/`media`:** fora do vocabulário de camadas.
- **Camada `landing/` pública:** mistura bruto e tratado e expõe campos pessoais do TSE.
- **Pasta `volumes/`:** termo de mercado, mas mais um nível; descartado pelo fundador por complexidade.
- **Fotos dentro de Parquet:** tudo seria tabela, mas o app não serviria cada foto por URL.
- **Bucket separado para arquivos:** descartado; o lake deve conter tudo.

## Consequências

- Cerca de 1 GB e 50 mil objetos a mais no R2, dentro da faixa gratuita.
- O `export` ganha um passo de arquivos; `fotos` deixa de ser só local.
- O landing do TSE continua só local (risco do 0036 mantido); só DOU e fotos publicam.
