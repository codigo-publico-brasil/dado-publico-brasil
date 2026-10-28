# ADR 0032: o partido de cada pessoa vem de fontes oficiais, e a filiação por data fica de fora

- **Status:** proposto (2026-10-27); decisão do fundador na conversa de 27/10/2026
- **Data:** 2026-10-27
- **Altera:** o item 10 do [ADR 0030](0030-modelo-de-dados-pessoa-no-centro.md) (que adiava a filiação do TSE e só valia o histórico da Câmara).

Para quem precisa saber de onde vem o partido de uma pessoa e o que ficou de fora de propósito. A base legal e os dados pessoais estão em [`../03-consultar/05-lgpd-dados-pessoais.md`](../03-consultar/05-lgpd-dados-pessoais.md).

## Contexto

O ADR 0030 deixou a filiação partidária do TSE para depois da decisão de LGPD (#38) e dizia que, antes dela, valeria o histórico da Câmara. Mas a Câmara só cobre deputados: com a F3, 322 mil pessoas (vereadores, prefeitos, governadores, senadores) não teriam partido algum. Em dado real, cerca de 5.800 pessoas oficiais e quase todos os eleitos municipais ficariam sem partido só olhando o histórico da Câmara.

## Decisão

1. **`fatos.pessoas_partidos`** guarda o partido de cada pessoa em cada momento, com a **base** de cada linha:
   - `candidatura`: o partido pelo qual a pessoa concorreu em cada eleição (arquivo de candidaturas do TSE, já carregado). Cobre toda pessoa que já foi eleita, inclusive quem nunca esteve na Câmara.
   - `historico_de_deputados`: os períodos do histórico da Câmara.
   - `inicio_da_legislatura`: o partido no início de cada legislatura, para deputados sem períodos no histórico.
   - `votos`: o partido do parlamentar em cada voto (Câmara e Senado), só para quem não tem histórico.
2. **Partido da candidatura não é data de filiação.** Ele diz por qual partido a pessoa concorreu naquela eleição; a coluna `ano_referencia` diz o ano, e nenhuma data de filiação é inventada ou completada.
3. **O arquivo de filiados do TSE (filiação por data) não é carregado.** Ele traz dado pessoal sensível (filiação a partido político, art. 5º, II da LGPD) de milhões de eleitores, não só de agentes públicos, sem necessidade para responder quem governa. Só entra com base legal escrita e decisão do fundador.
4. **Pessoa sem partido** (registro "S.Part.", "Sem registro", deputados anteriores a 1996 sem partido curado) fica sem `id_partido`, e o teste `pessoas_sem_partido` mede quantas.

## Alternativas consideradas

- **Só o histórico da Câmara:** deixa milhares de pessoas oficiais e quase todos os eleitos municipais sem partido. Rejeitada.
- **Carregar o arquivo de filiados do TSE:** dá datas de filiação, mas amplia o dado pessoal sensível para quem nunca foi agente público. Rejeitada por ora.
- **Inferir partido pela coligação ou pelo número:** viola a regra de nunca inferir. Rejeitada.

## Consequências

- Medido em dado real: 319.086 das 322.718 pessoas têm partido; todo eleito do TSE tem. As 3.632 sem partido são todas parlamentares do cadastro da Câmara ou do Senado sem candidatura, voto nem histórico com partido curado (em geral anteriores a 1996), e o teste `pessoas_sem_partido` as mede.
- A troca de partido entre eleições é visível (duas candidaturas seguidas com partidos diferentes), mas a data da troca não é conhecida.
- Quem precisar da data exata de filiação terá de abrir uma decisão nova sobre o arquivo de filiados.
