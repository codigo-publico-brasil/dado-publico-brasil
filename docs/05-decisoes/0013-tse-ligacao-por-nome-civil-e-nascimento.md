# ADR 0013: TSE (primeira fonte do Judiciário) e ligação por nome civil e nascimento

- **Status:** aceito (2026-10-21, pelo fundador)
- **Data:** 2026-10-21
- **Altera:** a regra de ligação de pessoas da spec 008 ("nunca ligar só por nome"), só para o par exato nome civil mais data de nascimento. Complementa o [ADR 0011](0011-buscar-ler-custom-e-chave-por-fonte.md) e o [ADR 0012](0012-dataset-por-item-lotes-com-envelope.md).

## Contexto

O TSE (Justiça Eleitoral, classificado como `judiciario/federal`) publica as candidaturas de cada eleição, com partido, cargo e resultado. É a fonte para saber o partido de quem concorreu, se foi eleito ou suplente e, principalmente, para **ligar quem foi deputado e depois senador**, hoje duas pessoas. O TSE não tem identificador estável da pessoa: o sequencial do candidato muda a cada eleição, e o que une as eleições (e as casas) é o CPF, que a plataforma não guarda.

## Decisão

1. **Fonte nova, `sources/judiciario/federal/tse.yml`.** Um pacote `.zip` por eleição geral (1998 a 2026, a cada 4 anos: `step: 4`), lido sem extrair (`archive: zip`) e só o membro `*_BRASIL.csv`, que reúne os estados (os demais só duplicariam). O landing guarda o pacote original, com hash.
2. **Minimização na declaração.** CPF, título de eleitor, e-mail e nome social não estão em `columns` e nunca entram no raw (o teste confere). `only` deixa passar só as candidaturas ao Congresso: deputado federal, senador e os suplentes de senador (a filtragem é por valor de coluna, declarada no YAML, e vale para qualquer fonte).
3. **Regra de ligação (opção A).** Dois registros são a mesma pessoa quando têm **nome civil e data de nascimento iguais** (nome sem acento, em minúsculas e com espaços únicos) e esse par é **único**:
   - dentro de cada fonte (Câmara, Senado) só um registro tem o par; se houver dois (homônimo com a mesma data), nada liga e o teste `pessoas_ambiguas_entre_fontes` mede;
   - numa eleição, só uma candidatura tem o par; senão a candidatura não liga.
   Cada vínculo grava o método e a data em `identity.pessoa_identificador`. Casos ambíguos ou sem correspondência (nome diferente entre as fontes, nascimento ausente) ficam sem vínculo e são medidos (`eleitos_federais_sem_vinculo`); a curadoria manual os resolve.
4. **Fusão entre casas.** Quando a regra mostra que um deputado e um senador são a mesma pessoa, a chave mais nova é absorvida pela mais antiga: os identificadores passam à chave sobrevivente, a chave absorvida sai de `identity.pessoa` e nunca é reaproveitada, e a fusão fica em `identity.pessoa_fusao` (mart `fusoes_de_pessoas`) para quem guardou a chave antiga. A operação é idempotente.
5. **`marts.pessoas` é uma linha por pessoa**, com os dados da Câmara quando a pessoa está nas duas casas e a coluna `fontes` com todas as fontes.
6. **A data de nascimento do senador** vem do detalhe (`/senador/{código}`, um dataset por item, [ADR 0012](0012-dataset-por-item-lotes-com-envelope.md)), que também traz naturalidade e foto; e-mail, telefone e endereço do gabinete não são lidos.
7. **Só candidaturas de quem já é pessoa do projeto** ficam expostas (`marts.candidaturas`). As demais (dezenas de milhares por eleição) ficam no staging: não há página de quem não foi eleito.
8. **Licença:** os conjuntos do portal declaram Creative Commons Attribution (CC BY): a fonte deve ser citada, o que o projeto já faz em todo dado.

## Fora do escopo desta entrega

Bens declarados, redes sociais, fotos, certidões, coligações, vagas e votação por candidato ou município. O resultado de cada candidatura (eleito por quociente ou por média, suplente, não eleito) já vem em `marts.candidaturas`.

## Alternativas consideradas

- **Hash com chave secreta do CPF:** liga exato, mas continua sendo identificador pessoal pseudonimizado e exige gestão de segredo.
- **Só vínculo manual:** seguro, mas não escala.

## Consequências

- Quem foi deputado e senador passa a ter uma só chave de pessoa quando o nome civil e o nascimento coincidem nas duas fontes; os demais continuam com duas, e isso é medido.
- Mudança de grafia do nome entre as fontes impede a ligação; a regra é conservadora de propósito (preferimos separar a juntar errado).
- O raw do TSE guarda nome e nascimento de candidatos ao Congresso de várias eleições (público, publicado pelo TSE); a exposição nos marts fica restrita a quem já é parlamentar.
