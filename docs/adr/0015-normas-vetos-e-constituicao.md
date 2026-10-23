# ADR 0015: Normas, vetos e Constituição (fontes e regras)

- **Status:** aceito (2026-10-23, pelo fundador)
- **Data:** 2026-10-23
- **Complementa:** o [ADR 0011](0011-buscar-ler-custom-e-chave-por-fonte.md) (módulo próprio por fonte), o [ADR 0012](0012-dataset-por-item-lotes-com-envelope.md) (dataset por item) e o [ADR 0013](0013-tse-ligacao-por-nome-civil-e-nascimento.md) (regra de ligação de pessoas).

## Contexto

Para ligar a decisão à lei, e a emenda ao artigo que ela mudou, a plataforma precisa do catálogo das normas, do que as alterou, dos vetos e do texto da Constituição. A pesquisa de fonte (23/10/2026) comparou o que está disponível de forma automatizável: o LexML está atrás de verificação anti-robô, o Planalto não abre da rede de desenvolvimento e a rota interna do `normas.leg.br` não é documentada. A API de dados abertos do Senado cobre normas, relações e vetos, e a Câmara publica o texto atualizado da Constituição.

## Decisão

1. **Normas, relações e vetos vêm da API do Senado**, declarados em `sources/legislativo/federal/senado.yml`, sem código próprio: `normas` (catálogo por ano, desde 1808), `normas_detalhe` (por item: publicações e relações de leis, leis complementares, emendas e medidas provisórias), `normas_detalhe_constituicao` (a Constituição, um documento), `vetos` (por ano, desde 1994), `vetos_dispositivos` e `vetos_votos` (por item).
2. **A Constituição vem do HTML da Câmara**, numa fonte própria (`sources/legislativo/federal/constituicao.yml`) com módulo próprio. A página lista o arquivo atual, e o nome muda a cada emenda: o módulo lê a página, escolhe o link com a emenda mais alta e guarda o arquivo original, sem alterar, com hash. O raw guarda uma linha por parágrafo (`ordem`, `linha`); a classificação em título, artigo, parágrafo, inciso e alínea é SQL do dbt, onde fica testada. `html` entra como formato do contrato e exige `records` no módulo próprio.
3. **O texto é fiel.** `constituicao_dispositivos.texto` é a linha como publicada, com a indicação da emenda; nada é reescrito. `constituicao_alteracoes` extrai cada nota entre parênteses (tipo pelas palavras da nota, número da emenda logo depois de "Emenda Constitucional nº"). O ano só é preenchido quando a nota cita uma emenda.
4. **Conferência cruzada entre duas fontes oficiais.** As emendas que o texto da Câmara cita como alteração devem constar entre as alterações permanentes que o Senado declara para a Constituição (`emendas_do_texto_desconhecidas_do_senado`), e nenhuma emenda citada pode ser posterior à versão do arquivo (`constituicao_cita_emenda_posterior_ao_arquivo`). O inverso não vale: o texto só cita a última emenda de cada trecho.
5. **Voto nominal dos vetos não é ligado a pessoas.** A fonte traz nome, partido e UF, sem código do parlamentar. A regra do ADR 0013 não liga só por nome; o voto é publicado como a fonte entrega, em `marts.votos_em_vetos`, sem `id_pessoa`. Ligá-lo exige uma regra nova, decidida em outro ADR.
6. **O texto das leis comuns fica de fora** até haver uma fonte oficial automatizável e com termos conhecidos (Planalto da rede de produção, LEGIN da Câmara ou a rota documentada do `normas.leg.br`).
7. **Datasets por item encadeados** (`vetos_dispositivos` lista os itens de `vetos`; `vetos_votos`, os de `vetos_dispositivos`): o pipeline carrega o raw depois de cada dataset por item, então a cadeia roda numa execução só; um dataset por item cuja origem ainda não foi carregada não tem itens, e não falha.
8. **Termos.** O portal do Senado permite o uso "desde que seja citada a fonte e para fins lícitos" e não nomeia licença; o `normas.leg.br` declara Creative Commons Atribuição 4.0 nos metadados; o `robots.txt` da Câmara não restringe a página da Constituição. Toda linha publicada leva a página oficial (`fonte_url`) e a data de captura.

## Alternativas consideradas

- **LexML:** é a fonte natural de texto estruturado, mas está atrás de verificação anti-robô, que não se contorna.
- **Planalto (texto compilado):** é o padrão de mercado, mas a conexão é derrubada da rede de desenvolvimento; fica como candidato para o texto das leis comuns.
- **Rota interna do `normas.leg.br`:** não documentada, respondeu 400 a todas as variações; não é base confiável.
- **Ligar o voto dos vetos por nome, UF e partido:** possível, mas é regra nova de identidade; não entra sem ADR próprio.
- **Classificar o HTML em Python:** funcionaria, mas o SQL do dbt já tem testes de reconciliação e o texto original fica intacto no raw.

## Consequências

- Os marts `normas`, `normas_relacoes`, `normas_publicacoes`, `vetos`, `dispositivos_vetados`, `votos_em_vetos`, `constituicao_dispositivos` e `constituicao_alteracoes` entram, e `normas_geradas` ganha `norma_id` (ligação ao catálogo).
- A carga total do detalhe (cerca de 25 mil normas, umas 7 horas) e dos vetos (dispositivos e votos) é decisão de quem opera; até lá o banco tem amostra dos mais recentes.
- Uma emenda constitucional nova atualiza o arquivo da Câmara; o próximo `plataforma run` baixa a versão nova, o raw a substitui e o landing guarda as anteriores.
- Se a Câmara mudar a formatação do arquivo, a leitura pode perder dispositivos; os testes de reconciliação existem para denunciar isso.
