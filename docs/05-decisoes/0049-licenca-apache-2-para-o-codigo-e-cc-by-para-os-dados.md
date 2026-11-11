# ADR 0049: Apache-2.0 para o código e CC BY 4.0 para os dados curados

- **Status:** aceito (2026-11-11)
- **Data:** 2026-11-11

Para quem decide, contribui ou quer reutilizar o projeto. Responde: qual licença vale, por quê e o que ela não resolve.

## Contexto

O repositório é público e não tinha licença: pelo padrão legal, todos os direitos ficam reservados e ninguém pode reutilizar o código nem os dados curados (issue 32). O plano anterior era AGPL-3.0 para o código e CC BY 4.0 para os dados.

Um levantamento de 11/11/2026 em doze projetos de dados abertos comparáveis (PUDL, Our World in Data, OpenSanctions, Open States, Kingfisher/Pelican, `unitedstates/congress`, Base dos Dados, Querido Diário, DadosJusBr, Brasil.IO, Serenata de Amor, EveryPolitician) (licenças lidas na API do GitHub) achou sete com código MIT, os demais com BSD, GPL ou CC0, só o repositório de pipelines da Base dos Dados sem licença declarada, e **nenhum com AGPL**. O objetivo do projeto é ser adotado por órgãos públicos, jornalistas e outros países, que em geral não podem ou não querem adotar copyleft forte.

## Decisão

1. **Código: Apache-2.0** (arquivos `LICENSE` e `NOTICE`, campo `license` do `pyproject.toml`).
2. **Dados curados: CC BY 4.0**: quem reutiliza cita o projeto e o `id_execucao` (`CITATION.cff`).
3. **Os termos de cada fonte oficial continuam valendo** e o manifesto os declara por tabela (chave `licenca` do contrato da fonte, issue 267). Os originais do Diário Oficial da União seguem a licença da Imprensa Nacional (CC BY-ND 3.0): redistribuição inteira, sem modificação, com a fonte citada.
4. Contribuições entram sob a mesma licença do código (Apache-2.0, seção 5), sem acordo de cessão.

## Alternativas consideradas

- **AGPL-3.0:** obriga quem oferece o serviço modificado a abrir o código e impede a apropriação fechada. Em troca, afasta órgãos públicos e empresas que não aceitam copyleft forte, e nenhum dos doze comparados a usa. Os dados, que são o valor do projeto, já são protegidos por atribuição. Rejeitada.
- **MIT:** a mais comum entre os comparados e mais curta, mas sem a cláusula de patentes que a Apache-2.0 traz. Rejeitada por pouco; seria aceitável.
- **Deixar sem licença:** mantém todos os direitos reservados e contradiz o objetivo. Rejeitada.
- **CC0 para os dados:** dispensaria a atribuição, mas perderia a citação da execução, que é o que torna o número reproduzível. Rejeitada.

## Consequências

- Qualquer pessoa pode copiar, modificar e redistribuir o código, inclusive em produtos fechados. O projeto não impede isso; a proteção é a atribuição dos dados e o nome.
- A licença dos dados **não** substitui a das fontes: onde a fonte restringe (CC BY-ND, uso comercial sem autorização), a restrição vale e precisa estar no manifesto antes de qualquer republicação.
- O texto da licença dos dados fica na página do lake e em `NOTICE`; a seção "Como citar" do [consumo do lake](../03-consultar/06-consumir-o-lake.md) acompanha a versão citável (issue 274).
- A licença é difícil de endurecer depois: quem já recebeu o código sob Apache-2.0 o mantém.
