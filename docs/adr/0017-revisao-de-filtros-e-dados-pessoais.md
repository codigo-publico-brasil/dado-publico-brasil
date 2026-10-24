# ADR 0017: Revisão de filtros, chaves e sinalização de dados pessoais

- **Status:** aceito (2026-10-24, pelo fundador)
- **Data:** 2026-10-24
- **Substitui em parte:** o [ADR 0016](0016-bens-votos-e-emendas.md), itens 1 e 5 (favorecidos), e a chave de candidatura do [ADR 0013](0013-tse-ligacao-por-nome-civil-e-nascimento.md).

## Contexto

A auditoria de 24/10/2026 comparou, arquivo a arquivo, o que a fonte entrega com o que chegou ao raw e aos marts. Achou perda silenciosa de dados: candidaturas de 2002 e 2006 e bens de 2006 colapsados por chave que repetia; cargos filtrados por `only` na declaração; autores sem pessoa descartados nas autorias; textos de ano e código convertidos em número; um filtro `like '%Emenda%'` na Constituição; e linhas rejeitadas pelo carregador sem ninguém ver.

## Decisão

1. **Candidatura é identificada por ano, unidade eleitoral e `SQ_CANDIDATO`** (`ano:SG_UE:sq`). O sequencial só é único dentro da unidade (UF, ou `BR` para presidente).
2. **O raw guarda tudo o que a fonte entrega**: sem `only` nas candidaturas (todos os cargos) nem nos favorecidos. Os marts é que escolhem.
3. **Chave sem identificador natural usa o conteúdo da linha** (`_row_hash`), como nos bens.
4. **Autorias mantêm os autores que não são pessoa** (comissões, órgãos), com `nome_autor` e `tipo_autor`; `id_pessoa` é opcional.
5. **Anos e códigos ficam como a fonte publica** (`ano_inicio_original`, códigos de função em texto); a versão numérica é derivada.
6. **O carregador sempre presta contas:** lidas, filtradas, carregadas, rejeitadas e colisões de chave (mesma chave, conteúdo diferente) viram um registro `carga` por carga; rejeição e colisão são erro.
7. **Favorecidos entram como o dado público os traz** (revisa o ADR 0016, item 5), sinalizados como dado pessoal.
8. **Dado pessoal é sinalizado em três níveis:** classe de sensibilidade `publico-dados-pessoais-de-terceiros` na tabela (e a tabela não pode ser `publica`); `meta: {pii: true}` nas colunas; `contem_dado_pessoal` na linha. O catálogo mostra a coluna "Dado pessoal".
9. **Os vínculos do TSE são derivados:** a cada execução saem os que a regra não propõe mais; aprovações manuais ficam.

## Alternativas consideradas

- **Manter o filtro e documentar:** esconde o que a fonte publica e foi a causa das perdas.
- **Excluir favorecidos pessoa física:** foi a decisão anterior; o fundador preferiu manter o dado público e sinalizar.

## Consequências

- Mais linhas no raw (candidaturas 180.970; bens 510.172; favorecidos 828.419); candidaturas ligadas a pessoas passaram de 6.709 para 10.790.
- Consumidores dos favorecidos devem tratar o dado como pessoal (LGPD).
- Todo filtro novo precisa aparecer no balanço da carga.
