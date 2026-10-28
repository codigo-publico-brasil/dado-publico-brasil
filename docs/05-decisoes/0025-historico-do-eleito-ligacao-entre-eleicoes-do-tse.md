# ADR 0025: histórico do eleito pela ligação entre as eleições do TSE

- **Status:** proposto (2026-10-26); aprovado pelo fundador na conversa de 26/10/2026
- **Data:** 2026-10-26
- **Complementa:** [ADR 0013](0013-tse-ligacao-por-nome-civil-e-nascimento.md) (ligação com a Câmara e o Senado) e [ADR 0023](0023-eleitos-escopo-regras-e-fontes.md) (eleitos).

## Contexto

O ADR 0013 liga a candidatura do TSE a uma pessoa da Câmara ou do Senado. Governador, prefeito, vereador e deputado estadual que nunca passaram pelo Congresso não têm pessoa no projeto, então a ficha do eleito não mostra o histórico dele, embora o TSE tenha as eleições anteriores (1996 a 2026). Na comparação com o Nexo, 6 deputados federais eleitos em 2022 saíam como novatos por falta de ligação (issue #72).

## Decisão

1. **Mesma pessoa, entre eleições do TSE:** duas candidaturas são da mesma pessoa quando têm o mesmo nome civil (sem acento, minúsculas, espaços únicos) e a mesma data de nascimento, e a combinação é **única em cada eleição**. Se duas candidaturas da mesma eleição têm a combinação (homônimo), nenhuma liga. Datas de 1º de janeiro ficam de fora, porque o TSE usa o dia 1º de janeiro quando só conhece o ano, e isso juntaria pessoas diferentes. Modelo `int_tse_pessoas`.
2. **Não cria pessoa:** o identificador (`id_pessoa_tse`) só diz quais candidaturas são da mesma pessoa; não entra em `identity` e não substitui o `id_pessoa` da Câmara e do Senado.
3. **Histórico só de quem foi eleito:** `eleitos_historico` traz, para cada eleito, as candidaturas anteriores de qualquer cargo (uma por eleição e cargo, pelo último turno). Quem só concorreu continua sem página (ADR 0013, item 7).
4. **Tipo de mandato por prova do TSE:** para deputado federal e senador sem pessoa do projeto, `tipo_mandato` é `reeleito` se foi eleito para o mesmo cargo na eleição anterior e `retorno` se foi eleito antes disso. Sem prova, fica vazio: nunca novato. Para quem tem pessoa do projeto, vale a regra dos mandatos (ADR 0023).
5. **O que o TSE não diz:** a eleição não registra afastamentos, cassação nem renúncia. O site mostra o mandato previsto, com esse aviso.

## Alternativas consideradas

- **Ligar pelo CPF:** liga exato, mas coloca documento pessoal no raw (a minimização do ADR 0013 o exclui).
- **Só vínculo manual:** seguro, mas não escala para meio milhão de eleitos.

## Consequências

- Conservador de propósito: mudança de nome entre eleições, nascimento ausente (121 mil candidaturas, em eleições antigas) ou nascimento em 1º de janeiro impedem a ligação, e a ficha diz que o histórico não está confirmado. Medido: em 3,69 milhões de candidaturas, 3,54 milhões ligam e 6,4 mil combinações ficam ambíguas.
- Existe risco de ligar duas pessoas diferentes com o mesmo nome e a mesma data de nascimento em eleições diferentes. A regra o reduz exigindo unicidade na eleição; a conferência com uma fonte independente (o Nexo) é parte do teste de lacunas.
- Medido em 2026 (deputados federais): 3 que saíam sem selo passaram a reeleito pela prova do TSE (os 2 que o Nexo conta como reeleitos e mais 1). Outros 4 dos 6 casos da comparação com o Nexo continuam sem ligação porque o nome civil mudou entre 2022 e 2026 (casos de nome civil que mudou entre 2022 e 2026). Uma segunda chave, nome de urna mais data de nascimento, os ligaria; fica como melhoria (issue 77), porque exige agrupar as duas chaves.
- O raw já guardava nome e nascimento de todos os candidatos (públicos, publicados pelo TSE). A exposição nos marts continua restrita a quem foi eleito.
