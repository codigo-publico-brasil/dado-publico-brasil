# ADR 0050: dado pessoal que a fonte oficial publica vem para o lake como a fonte publica

- **Status:** aceito (2026-11-11); revisão jurídica pendente (issue 38)
- **Data:** 2026-11-11
- **Complementa:** [ADR 0017](0017-revisao-de-filtros-e-dados-pessoais.md) (CPF e documentos pessoais continuam fora) e [ADR 0032](0032-partido-da-pessoa-por-fonte-e-filiacao.md).
- **Para quem é:** quem decide o que o lake pode publicar e quem opera o projeto. Responde: que dado pessoal entra como a fonte publica, com que base e o que isso exige depois. Rascunho jurídico por tabela: [LGPD e dados pessoais](../03-consultar/05-lgpd-dados-pessoais.md).

## Contexto

O projeto mascarava parte do que as fontes oficiais publicam (por exemplo, número de conta bancária em descrições de bens e despesas, no staging do TSE) e discutia cortar a data de nascimento de `dim_pessoas` para só o ano ([issue 38](https://github.com/codigo-publico-brasil/dado-publico-brasil/issues/38)). Isso conflita com o objetivo de auditabilidade: o público precisa comparar o lake com a fonte, e um dado alterado por nós deixa de bater com ela. O dado já está público na origem.

## Decisão

1. **Dado pessoal que a fonte oficial publica vem para o lake como a fonte publica**, sempre com fonte, URL e data de captura: data de nascimento completa em `dim_pessoas` e número de conta bancária dentro de descrições de bens e despesas.
2. **Continuam fora:** CPF e outros documentos pessoais (RG, título de eleitor), por regra do `AGENTS.md` e do [ADR 0017](0017-revisao-de-filtros-e-dados-pessoais.md), mesmo quando a fonte os publica. Não se infere nem se completa dado que a fonte não traz.
3. **Base legal e finalidade (proposta, a validar):** Lei 13.709/2018 (LGPD), art. 7º, § 3º: "O tratamento de dados pessoais cujo acesso é público deve considerar a finalidade, a boa-fé e o interesse público que justificaram sua disponibilização". Finalidade aqui: controle social e transparência sobre agentes e gastos públicos. O § 4º dispensa o consentimento para dados "tornados manifestamente públicos pelo titular", mas ressalva os direitos do titular e os princípios da lei; como aqui quem publica é o Estado, e não o titular, o § 4º não basta sozinho, e por isso a revisão jurídica abaixo é condição. Texto: [planalto.gov.br](https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709.htm).

## Alternativas consideradas

- **Publicar só o ano de nascimento e mascarar conta:** reduz o risco, mas o lake deixa de espelhar a fonte e some a prova de origem; foi a prática anterior.
- **Não publicar `dim_pessoas`:** perde a ficha da pessoa, que é o centro do modelo ([ADR 0030](0030-modelo-de-dados-pessoa-no-centro.md)).

## Consequências

- **Coerência da máscara:** o staging do TSE ainda mascara conta em `stg_tse__bens` e `stg_tse__despesas_candidatos` (modo `bem` de `mascarar_dado_pessoal`). Publicar a mesma informação sem máscara em outras fontes e mascarada nelas é incoerente; a máscara de conta deve ser reavaliada (manter para todas, por precaução, ou retirar de todas). Pendente de decisão, acompanhada na issue 38.
- **Canal do titular:** o pedido de correção ou remoção entra pelo relato privado descrito em [`SECURITY.md`](../../SECURITY.md), sem enviar o dado pessoal; o lake volta ao que a fonte publica, e a fonte é quem corrige a origem.
- **Revisão jurídica pendente (fundador, issue 38):** este ADR só passa a aceito depois dela; se ela exigir, nasce ADR novo.
