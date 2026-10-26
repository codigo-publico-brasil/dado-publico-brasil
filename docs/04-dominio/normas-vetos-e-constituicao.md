# Normas, vetos e Constituição: o que os dados dizem

Para quem quer entender os campos que a plataforma traz sobre a lei. As fontes e os limites estão no [catálogo de fontes](../03-consultar/03-fontes-de-dados.md); a decisão, no [ADR 0015](../05-decisoes/0015-normas-vetos-e-constituicao.md).

## Norma

**Norma** é o ato jurídico publicado: lei, lei complementar, emenda constitucional, medida provisória, decreto, decreto legislativo, resolução. `marts.normas` é o catálogo (tipo, número, data, ementa, link oficial); o texto integral não vem desta fonte. O tipo vem como sigla da fonte (`LEI-n` lei numerada, `LCP` lei complementar, `EMC-n` emenda constitucional, `MPV-cs` e `MPV-ss` medida provisória, `DEC-n` decreto, `DLG` decreto legislativo). Decretos são do Poder Executivo e entram no catálogo sem detalhe.

`marts.normas_relacoes` diz o que aconteceu com cada norma depois, como o Senado declara: alteração permanente, regulamentação, veto, declaração de constitucionalidade. `marts.normas_publicacoes` diz onde saiu no Diário Oficial (edição, página e coluna), incluindo a publicação do veto quando houve.

## Veto

Depois de aprovado pelo Congresso, o projeto vai à sanção. O Presidente pode **vetar** o projeto inteiro (veto total) ou partes dele (veto parcial), e deve escrever a **razão do veto**. O Congresso, em sessão conjunta de deputados e senadores, aprecia o veto, **dispositivo por dispositivo**: o veto pode ser **mantido** (o trecho vetado não vale) ou **rejeitado** (o Congresso derrubou o veto e o trecho vale). Há ainda "prejudicado" e "não apreciado" (ainda não votado). `marts.vetos` traz o veto, a matéria vetada e a norma que ela gerou; `marts.vetos_dispositivos`, o texto vetado, a razão e a situação como a fonte informa; `marts.votacoes_votos_em_vetos`, o voto nominal (nome, partido, UF e voto), **sem ligação a `pessoas`**, porque a fonte não traz o código do parlamentar.

## Constituição

A Constituição de 1988 tem a parte permanente e o **ADCT** (Ato das Disposições Constitucionais Transitórias), que cada emenda pode alterar. A Câmara publica o texto já consolidado, com a indicação entre parênteses de cada emenda que mudou um trecho: "(Redação dada pela Emenda Constitucional nº 45, de 2004)".

`marts.constituicao_dispositivos` traz o texto dispositivo a dispositivo, com o caminho (`Art. 5, XLII`, `Art. 14, § 1, I, a)`), o título e o capítulo, e a emenda até a qual o arquivo está atualizado. `marts.constituicao_alteracoes` traz uma linha por dispositivo e emenda citada, com o tipo (redação dada, incluído, revogado, suprimido, renumerado ou vide, que é só referência). O texto só cita a emenda mais recente de cada trecho: para o histórico completo de alterações do Senado, veja `normas_relacoes` da norma 579494.

> **Conceito: fidelidade ao texto.** A plataforma não reescreve nem resume a lei: o texto é a linha publicada. Resumir para o público comum é trabalho de quem consome a plataforma, sobre este texto, com a fonte e a data de captura à vista.
