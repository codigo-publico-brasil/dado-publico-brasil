# LGPD: base legal, finalidade e retenção dos dados pessoais

**Rascunho para revisão do fundador e, se possível, de pessoa com formação jurídica.** Para quem decide se e como o projeto publica dado pessoal. Responde: que dado pessoal a plataforma guarda, em que base legal, para quê, por quanto tempo e como um titular pede correção ou remoção. Não é parecer jurídico: os artigos citados da Lei 13.709/2018 (LGPD) precisam de conferência. A classificação técnica (classes, `meta: pii`) está em [governança](06-governanca.md); as decisões, nos [ADR 0017](../05-decisoes/0017-revisao-de-filtros-e-dados-pessoais.md) e [ADR 0029](../05-decisoes/0029-campos-de-pessoas-nos-marts.md). Pendência: issue #38.

## Princípio

Dado publicado oficialmente continua sendo dado pessoal. "Público" não significa "livre de restrição": a LGPD permite tratar dado de acesso público, mas só para finalidade, boa-fé e interesse público que justifiquem a publicação (art. 7º, §§ 3º e 4º). A plataforma guarda o que a fonte oficial publica, com fonte e data, e não coleta nada além disso.

## Finalidade

Dar transparência sobre quem exerce ou disputa cargo público e sobre o uso do dinheiro público, de modo que o cidadão possa conferir a fonte oficial. Sem ranking, nota ou perfilamento de pessoas.

## Dados e base legal por tabela

| Dado pessoal | Onde está | Titular | Base legal proposta |
| --- | --- | --- | --- |
| Nome, nascimento, naturalidade, foto, redes e contato institucional | `pessoas`, `mandatos`, `eleitos` | agente público no exercício do cargo | dado de acesso público, tratado para transparência (art. 7º, § 3º), e publicidade da função pública |
| Dados declarados na candidatura (nome social, estado civil, grau de instrução, ocupação, coligação) | `candidaturas` | candidato | dado tornado público por lei eleitoral, tratado para a mesma finalidade (art. 7º, §§ 3º e 4º) |
| Partido do candidato | `candidaturas`, `eleitos` | candidato | filiação política é dado sensível (art. 5º, II), mas a candidatura por partido é pública por lei eleitoral e é o dado central da transparência. Base proposta: o art. 11, com a candidatura como ato público do titular. **Confirmar com jurídico.** |
| Patrimônio declarado | `candidaturas_bens` | candidato | dado de acesso público, finalidade de transparência |
| Nome e CPF mascarado de pessoa física que recebeu emenda | `emendas_favorecidos`, `emendas_convenios` | **cidadão comum** | dado de acesso público (art. 7º, § 3º), com CPF mascarado como a fonte publica; maior risco, ver abaixo |

Nunca entram em nenhuma camada: CPF, RG, título de eleitor, e-mail e telefone pessoais, e cor ou raça (decisão do fundador, para não acrescentar dado sensível). Certidões criminais ficam fora até decisão explícita.

## Retenção

- **Landing:** guarda o arquivo original, imutável, enquanto a fonte o publicar, porque é a prova de auditoria. Ele não é exposto ao público.
- **Marts:** refletem o que a fonte publica hoje. O que a fonte remover deve sair dos marts na carga seguinte (issue #24, linha removida pela fonte).
- **Tensão a decidir:** o landing imutável conflita com um pedido de remoção. Proposta: atender no mart e na aplicação de imediato, e manter o landing sob acesso restrito, registrando o pedido; ver a decisão abaixo.

## Direitos do titular (art. 18) e canal

Titular pode pedir confirmação, correção, anonimização ou eliminação. Fluxo proposto: o pedido chega por um canal de contato do projeto (**a definir pelo fundador**), a plataforma confere a fonte oficial e, se o dado estiver errado, a correção é da fonte (a plataforma não corrige por conta própria); se a fonte já removeu, a remoção segue na carga seguinte. Resposta em até 15 dias.

## Decisões que cabem ao fundador

1. Canal de contato dos titulares (e-mail ou formulário).
2. Confirmar com o jurídico a base para exibir o partido do candidato.
3. Remoção a pedido de cidadão comum nos favorecidos de emendas: remover do mart mesmo quando a fonte ainda publica?
4. Revisão jurídica antes de tornar o repositório público (#33).

## Critério de aceite da issue #38

- [x] documento com base legal por tabela com dado pessoal (rascunho)
- [ ] política de retenção aprovada
- [ ] canal para pedidos de titulares definido
- [ ] a classe `publico-dados-pessoais-de-terceiros` aponta para este documento
