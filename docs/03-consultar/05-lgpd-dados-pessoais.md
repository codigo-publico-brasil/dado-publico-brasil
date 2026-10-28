# Dados pessoais e LGPD

Para quem decide o que o projeto pode publicar e para quem consome os dados. Responde: quais dados pessoais o projeto trata, com que justificativa, por quanto tempo e como uma pessoa pede correção ou remoção. **É um rascunho para revisão do fundador e de quem tenha formação jurídica**: as bases legais abaixo são propostas, não pareceres. Acompanha a [issue 38](https://github.com/codigo-publico-brasil/dado-publico-brasil/issues/38).

Regra de partida: **dado publicado oficialmente continua sendo dado pessoal.** Público não quer dizer livre de restrição. O projeto só trata o que uma fonte oficial publica, guarda a URL e a data de captura, e nunca trata CPF, título de eleitor, e-mail pessoal ou certidões.

## O que é dado pessoal aqui

| Dado | Onde está | Natureza | Observação |
| --- | --- | --- | --- |
| Nome, nome de urna, data de nascimento e gênero de eleitos | `core.pessoas`, `fatos.candidaturas` | pessoal, de agente público | a data de nascimento é publicada pelo TSE no registro de candidatura |
| Partido da candidatura ou do mandato | `fatos.candidaturas`, `fatos.mandatos`, `fatos.pessoas_partidos` | pessoal; filiação partidária é **sensível** (LGPD, art. 5º, II) | ver o ADR 0032: só o partido de quem se candidatou ou exerceu mandato |
| Nome social, grau de instrução, estado civil | `fatos.candidaturas` | pessoal (`meta: pii`) | declarados no registro de candidatura; o TSE protege alguns como "não divulgável" |
| Bens, receitas e despesas de campanha | `fatos.campanhas`, `marts.candidaturas_bens` | pessoal patrimonial | prestação de contas obrigatória por lei |
| Favorecidos de emendas, pessoa física | `marts.emendas_favorecidos` | pessoal de terceiros (`publico-dados-pessoais-de-terceiros`) | CPF mascarado como o portal publica |
| Foto oficial do candidato | arquivos extraídos do pacote do TSE | pessoal | a hospedagem pública depende da decisão do VPS (#30) |
| Identidade (`id_pessoa`) | `identity.*` | chave interna | não se reconstrói; não é publicada |

Ficam fora do projeto, por regra: CPF, título de eleitor, e-mail, telefone pessoal, certidões criminais e o arquivo de filiados do TSE (ADR 0032).

## Base legal proposta (a validar)

| Tratamento | Base proposta | Finalidade |
| --- | --- | --- |
| Agentes públicos e candidatos: nome, nascimento, cargo, mandato, partido, votos, campanha | dado de acesso público (LGPD, art. 7º, §§ 3º e 4º), com finalidade de controle social e transparência; e legítimo interesse (art. 7º, IX) | responder quem governa, por que e como, com a fonte sempre rastreável |
| Filiação partidária (sensível) | tratamento limitado ao partido de quem se candidatou ou exerceu mandato, que consta do próprio registro público de candidatura | mostrar a trajetória partidária de agente público |
| Favorecidos de emendas, pessoa física | dado publicado pelo Portal da Transparência (art. 7º, § 4º), CPF mascarado | rastrear o destino do dinheiro público |
| Fotos | idem, só a foto oficial do registro | identificar o candidato |

Princípios que o projeto já cumpre: finalidade, adequação, necessidade (só o que responde à pergunta do projeto), transparência (toda linha com fonte, URL e data), segurança e não discriminação (sem ranking, nota nem inferência sobre pessoas).

## Retenção (proposta)

- **Enquanto a fonte oficial publicar:** o landing é imutável e guarda o que foi capturado, com hash e data.
- **Pessoa que pede remoção ou correção:** o dado volta ao que a fonte oficial publica; o que a fonte não publica mais deixa de ser mostrado nos serviços. O landing e a identidade não são apagados (são o registro do que foi capturado), mas a publicação (`publish` e o esquema `servico`) respeita o pedido.
- **Pessoa que nunca foi eleita:** não tem linha em `core.pessoas`; as candidaturas dela ficam em `fatos.candidaturas` com o que o TSE publica.

## Direitos dos titulares e canal

A LGPD dá ao titular acesso, correção, anonimização, eliminação e oposição. **O canal ainda não existe**: precisa ser decidido (por exemplo, uma caixa de e-mail do projeto ou um formulário no site) e divulgado no portal. Até lá, o pedido entra como issue sem dado pessoal no corpo, e a resposta é registrada.

## Decisões pendentes

1. Revisão jurídica das bases acima.
2. Canal de pedidos de titulares.
3. Se `core.pessoas` (322 mil pessoas, a maioria vereadores) entra na publicação e com quais campos (data de nascimento completa ou só o ano).
4. Se o arquivo de filiados do TSE algum dia entra (o ADR 0032 diz que não, por ora).
5. Retenção de pessoa que foi eleita e teve o resultado anulado.
