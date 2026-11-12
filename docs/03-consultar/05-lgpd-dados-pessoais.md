# Dados pessoais e LGPD

Para quem decide o que o projeto pode publicar e para quem consome os dados. Responde: quais dados pessoais o projeto trata, com que justificativa, por quanto tempo e como uma pessoa pede correção ou remoção. **É um rascunho para revisão do fundador e de quem tenha formação jurídica**: as bases legais abaixo são propostas, não pareceres. Acompanha a [issue 38](https://github.com/codigo-publico-brasil/dado-publico-brasil/issues/38).

Regra de partida: **dado publicado oficialmente continua sendo dado pessoal.** Público não quer dizer livre de restrição. O projeto só trata o que uma fonte oficial publica, guarda a URL e a data de captura, e nunca trata CPF, título de eleitor, e-mail pessoal ou certidões.

## O que é dado pessoal aqui

| Dado | Onde está | Natureza | Observação |
| --- | --- | --- | --- |
| Nome, nome de urna, data de nascimento e gênero de eleitos | `dim_pessoas`, `fct_candidaturas` | pessoal, de agente público | a data de nascimento é publicada pelo TSE no registro de candidatura |
| Partido da candidatura ou do mandato | `fct_candidaturas`, `fct_mandatos`, `fct_pessoas_partidos` | pessoal; filiação partidária é **sensível** (LGPD, art. 5º, II) | ver o ADR 0032: só o partido de quem se candidatou ou exerceu mandato |
| Nome social, grau de instrução, estado civil | `fct_candidaturas` | pessoal (`meta: pii`) | declarados no registro de candidatura; o TSE protege alguns como "não divulgável" |
| Bens, receitas e despesas de campanha | `fct_campanhas`, `fct_candidaturas_bens` | pessoal patrimonial | prestação de contas obrigatória por lei; a descrição vem como o TSE publica, inclusive agência e conta bancária que o candidato escreveu (ADR 0050, issue 289; só o CPF é mascarado). A republicação das tabelas afetadas, `stg_tse__bens`, `stg_tse__despesas_candidatos` e `fct_candidaturas_bens`, é do fundador, e a pendência jurídica segue na issue 38 |
| Favorecidos de emendas, pessoa física | `fct_emendas_favorecidos` | pessoal de terceiros (`publico-dados-pessoais-de-terceiros`) | CPF mascarado como o portal publica |
| Vencedor e participante de licitação, pessoa física | `fct_licitacoes_itens`, `fct_licitacoes_participantes` | pessoal de terceiros (`publico-dados-pessoais-de-terceiros`) | CPF mascarado pelo projeto (a fonte o publica completo); `fl_contem_dado_pessoal` marca a linha |
| Contratado de contrato federal, pessoa física | `fct_contratos` | pessoal de terceiros (`publico-dados-pessoais-de-terceiros`) | CPF mascarado pelo projeto (a fonte o publica completo); `fl_contem_dado_pessoal` marca a linha |
| Fornecedor pessoa física e texto livre da cota parlamentar | `fct_cotas_despesas` | pessoal de terceiros (`publico-dados-pessoais-de-terceiros`) | nome como a fonte publica; CPF mascarado pelo projeto (a fonte o publica completo); `fornecedor`, `documento_fornecedor` e `detalhamento` são `meta: pii` |
| Foto oficial do candidato | arquivos extraídos do pacote do TSE | pessoal | a hospedagem pública depende da decisão do VPS (#30) |
| Identidade (`id_pessoa`) | `identity.*` | chave interna | não se reconstrói; não é publicada |

Ficam fora do projeto, por regra: CPF, título de eleitor, e-mail, telefone pessoal, certidões criminais e o arquivo de filiados do TSE (ADR 0032).

## Base legal proposta (a validar)

| Tratamento | Base proposta | Finalidade |
| --- | --- | --- |
| Agentes públicos e candidatos: nome, nascimento, cargo, mandato, partido, votos, campanha | dado de acesso público (LGPD, art. 7º, §§ 3º e 4º), com finalidade de controle social e transparência; e legítimo interesse (art. 7º, IX) | responder quem governa, por que e como, com a fonte sempre rastreável |
| Filiação partidária (sensível) | tratamento limitado ao partido de quem se candidatou ou exerceu mandato, que consta do próprio registro público de candidatura | mostrar a trajetória partidária de agente público |
| Favorecidos de emendas, pessoa física | dado publicado pelo Portal da Transparência (art. 7º, § 4º), CPF mascarado | rastrear o destino do dinheiro público |
| Vencedor e participante de licitação, pessoa física | dado publicado pelo Portal da Transparência (art. 7º, § 4º), CPF mascarado | rastrear quem contrata com o poder público |
| Fornecedor pessoa física da cota parlamentar | dado publicado pela Câmara e pelo Senado (art. 7º, § 4º), CPF mascarado | acompanhar o uso da verba pública de exercício do mandato |
| Fotos | idem, só a foto oficial do registro | identificar o candidato |

Princípios que o projeto já cumpre: finalidade, adequação, necessidade (só o que responde à pergunta do projeto), transparência (toda linha com fonte, URL e data), segurança e não discriminação (sem ranking, nota nem inferência sobre pessoas).

## Retenção (proposta)

- **Enquanto a fonte oficial publicar:** o landing é imutável e guarda o que foi capturado, com hash e data.
- **Pessoa que pede remoção ou correção:** o dado volta ao que a fonte oficial publica; o que a fonte não publica mais deixa de ser mostrado nos serviços. O landing e a identidade não são apagados (são o registro do que foi capturado; o landing imutável conflita com um pedido de remoção, então ele fica sob acesso restrito e o pedido é registrado), mas a publicação (`publish` e o esquema `marts`) respeita o pedido.
- **Pessoa que nunca foi eleita:** não tem linha em `dim_pessoas`; as candidaturas dela ficam em `fct_candidaturas` com o que o TSE publica.

## Direitos dos titulares e canal

A LGPD dá ao titular acesso, correção, anonimização, eliminação e oposição. O canal é o relato privado do GitHub (aba **Security** do repositório), descrito em [`SECURITY.md`](../../SECURITY.md); o pedido não deve trazer o dado pessoal, só onde ele está. Ainda não há e-mail nem formulário, e falta divulgá-lo no site. A resposta é registrada.

## Decisões pendentes

1. Revisão jurídica das bases acima (fundador, issue 38).
2. Canal de pedidos de titulares: decidido que é o relato privado da aba Security do repositório, sem enviar o dado pessoal ([`SECURITY.md`](../../SECURITY.md)); falta divulgá-lo no site.
3. Decidido pelo fundador em 11/11/2026: `dim_pessoas` fica com a data de nascimento completa, e o dado pessoal que a fonte publica vem como está ([ADR 0050](../05-decisoes/0050-dado-pessoal-publicado-pela-fonte-vem-como-esta.md), proposto). Falta decidir se a máscara de conta bancária do staging do TSE sai, por coerência.
4. Se o arquivo de filiados do TSE algum dia entra (o ADR 0032 diz que não, por ora).
5. Retenção de pessoa que foi eleita e teve o resultado anulado.
