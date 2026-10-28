# ADR 0031: pessoas de todo eleito, ancoradas na candidatura

- **Status:** proposto (2026-10-27); fase F3 do [ADR 0030](0030-modelo-de-dados-pessoa-no-centro.md), aprovada pelo fundador na conversa de 27/10/2026
- **Data:** 2026-10-27
- **Altera:** [ADR 0004](0004-camadas-da-plataforma-de-dados.md) e [0013](0013-tse-ligacao-por-nome-civil-e-nascimento.md): a identidade deixa de criar pessoa só pelo identificador da Câmara e do Senado. A regra de ligação (nome civil e nascimento únicos, ADRs [0025](0025-historico-do-eleito-ligacao-entre-eleicoes-do-tse.md) e [0026](0026-segunda-chave-nome-de-urna-e-nascimento.md)) continua valendo.

Para quem mantém a identidade e quer saber o que mudou, por quê e o que ficou de fora. A lista viva de riscos e do teste de cada um está na [issue 130](https://github.com/codigo-publico-brasil/dado-publico-brasil/issues/130).

## Contexto

O ADR 0030 decidiu que `pessoas` é quem já teve pelo menos um cargo, inclusive vereador, e que a pessoa entra no momento da eleição. Até aqui só o parlamentar da Câmara e do Senado tinha pessoa (cerca de 8,5 mil); os 533 mil mandatos do TSE não tinham dono. A chave `id_pessoa` não se reconstrói do landing e não pode mudar depois de entregue, então a regra precisa ser conservadora e estável.

## Decisão

1. **Quem ganha pessoa:** todo candidato que foi eleito pelo menos uma vez (o TSE diz "Eleito", ou, em disputa de uma vaga que o TSE não fecha, como o 2º turno de presidente de 2006, vence o mais votado do último turno, pela Constituição: `base_eleicao = derivado`, só em eleição de ano passado e sem empate), a partir da primeira execução depois da eleição, mais todas as candidaturas do mesmo grupo (também as que perdeu). Quem só se candidatou e nunca foi eleito não tem pessoa.
2. **A âncora é `id_candidatura`, não `id_pessoa_tse`.** O `id_pessoa_tse` é um hash do menor rótulo do grupo e muda se entra uma candidatura com outro nome; usá-lo como identificador criaria pessoas duplicadas. A ponte `identity.pessoa_identificador` ganha um tipo novo, `candidatura_de_eleito`, com uma linha por candidatura do grupo. O tipo `candidato` continua só para o que liga a um parlamentar (os marts antigos dependem dele).
3. **Fusão:** se o grupo toca mais de uma pessoa, elas viram uma só. A pessoa oficial (Câmara ou Senado) sempre sobrevive, mesmo sendo a mais nova, para não mudar a chave já publicada do parlamentar. Entre pessoas só do TSE, sobrevive a de menor chave. A chave absorvida fica em `identity.pessoa_fusao`.
4. **Duas pessoas oficiais nunca se fundem por um grupo do TSE.** O grupo fica sem pessoa nova e o teste `pessoas_de_grupo_do_tse_com_mais_de_uma_pessoa` o aponta, para decisão à mão em `vinculos_aprovados`.
5. **`core.pessoas`:** uma linha por pessoa, com nome civil, nome público, nascimento e gênero, **cada um com a fonte de onde veio** (Câmara e Senado valem mais que o TSE; o TSE vale a candidatura mais recente que traz o dado). Gênero só quando a fonte diz masculino ou feminino. `marts.pessoas` não muda até a F6.
6. `fatos.candidaturas` e `fatos.mandatos` ganham `id_pessoa`.

## Alternativas consideradas

- **Ancorar em `id_pessoa_tse`:** mais simples, mas o rótulo muda e duplica pessoas. Rejeitada.
- **Pessoa para todo candidato:** milhões de pessoas privadas que só concorreram. Rejeitada no ADR 0030.
- **Fundir também duas pessoas oficiais quando o grupo as une:** poderia unir dois parlamentares homônimos por engano. Rejeitada: fica para revisão humana.
- **Pôr os eleitos novos em `marts.pessoas`:** quebraria os aplicativos antes da F6.

## Consequências

- Medido em dado real (cópia do warehouse): 314.201 pessoas novas; 928.4 mil candidaturas ligadas; 19 mandatos derivados dos votos (um presidente em 2006 e prefeitos de 2008, 2016 e 2020), 234 disputas de uma vaga ainda sem eleito (prefeitos sem votos fechados e a eleição de 2026 em curso); 3 mandatos ficam sem pessoa por um caso de grupo que toca um deputado e um senador (Goiás, a conferir).
- Cerca de 21 mil pessoas ficam sem data de nascimento porque o TSE não a informa; nelas a ligação entre eleições não existe e cada eleição pode ter virado outra pessoa. Medido, não corrigido.
- Suplente que assumiu vaga de vereador, deputado estadual ou prefeito/vice não tem pessoa nem exercício: não há fonte oficial carregada.
- Os identificadores já entregues não mudam; a identidade é idempotente (rodar de novo não cria nem funde nada).
