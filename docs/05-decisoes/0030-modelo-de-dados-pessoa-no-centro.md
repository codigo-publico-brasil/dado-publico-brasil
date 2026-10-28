# ADR 0030: modelo de dados com a pessoa no centro, eventos tipados e composições

- **Status:** proposto (2026-10-27); aprovado pelo fundador na conversa de 27/10/2026
- **Data:** 2026-10-27
- **Altera:** [ADR 0023](0023-eleitos-escopo-regras-e-fontes.md) (o mart `eleitos` e os derivados dele serão substituídos, fase a fase) e a organização de marts da [ADR 0007](0007-dois-pacotes-e-camadas-de-mercado.md) (os marts por pergunta dão lugar a esquemas por papel). As regras de ligação de pessoas ([0013](0013-tse-ligacao-por-nome-civil-e-nascimento.md), [0025](0025-historico-do-eleito-ligacao-entre-eleicoes-do-tse.md), [0026](0026-segunda-chave-nome-de-urna-e-nascimento.md)) continuam valendo.

O desenho completo, com figuras, matrizes de eventos e dados a buscar, está em [`../01-entender/08-modelo-de-dados.html`](../01-entender/08-modelo-de-dados.html). Este ADR registra só a decisão.

## Contexto

Os marts cresceram por pergunta: `eleitos`, `candidaturas`, `eleitos_campanhas` e outros respondem coisas parecidas com grãos diferentes e misturam fontes. Casos reais numa aplicação consumidora mostraram o efeito (duas pessoas com carreira longa sem campanha, porque o mart só cobre quem venceu). A análise do warehouse em 27/10/2026 achou também texto no lugar de chave (partido, cargo, UF), 16 de 39 marts sem `dt_captura`, `pessoas` misturando cadastro com contagens, e `votacoes.proposicoes` como lista em texto. O objetivo do projeto é responder quem governa, por que governa e como governa, com dado aberto, curado e auditável.

## Decisão

1. **A pessoa é o eixo.** Toda tabela que fala de gente carrega `id_pessoa` (ou o identificador da fonte, enquanto a ligação não existe). Tabela nova só entra se declarar o grão em uma frase e explicar por que nenhuma existente comporta o dado.
2. **Quem entra em `pessoas`:** quem já teve pelo menos um cargo (eleito titular, suplente que assumiu, nomeado), inclusive vereadores. **A pessoa entra no momento de ser eleita**, antes da posse. Quem só se candidatou fica em `candidaturas` com o identificador do TSE, a foto e a campanha, sem linha em `pessoas`.
3. **Esquemas por papel:** `core` (pessoas, órgãos, cargos, territórios, partidos, eleições, disputas, catálogo de tipos de evento), `fatos` (candidaturas, resultados, campanhas, mandatos, exercícios, filiações e atos de atuação), `analise` (composições e agregados) e `servico` (views dos aplicativos, sem regra de negócio). O esquema `marts` é esvaziado aos poucos.
4. **Eventos:** os fatos tipados são a verdade; `eventos` é uma tabela única **derivada**, sem texto livre. O tipo vem do catálogo fechado `evento_tipos` (chave estrangeira e teste); tipo novo exige linha no catálogo, regra e teste. O detalhe fica no fato de origem.
5. **Mandato com vigência (SCD tipo 2)** em `mandatos` e `filiacoes`, mais cortes prontos em `analise.composicoes` (posse, 1º de janeiro e 1º de julho). Composição **eleita** e composição **em exercício** são sempre separadas.
6. **Datas derivadas do calendário legal** só onde não há fonte de exercício, com o artigo citado, `cd_base = derivado` e sem nunca sobrescrever dado de fonte.
7. **Chaves no lugar de texto:** `id_partido`, `id_cargo`, `id_orgao` e `id_territorio` em todo fato; o texto da fonte fica ao lado (`*_na_fonte`) para auditoria.
8. **Rastreio:** toda tabela de fato carrega `id_captura` (liga a `metadata.captures`: URL, data, hash), com teste.
9. **Declarações, não eventos de vida:** estado civil, instrução, ocupação e bens ficam como declaração na data da candidatura. Casamento e separação não existem em dado aberto e não são inferidos.
10. **Filiação partidária do TSE** fica adiada até a decisão de LGPD (#38); antes dela vale a troca de partido do histórico da Câmara.
11. **Aposentadoria:** `eleitos*` e `candidaturas` saem quando o novo modelo cobrir o que entregam e o aplicativo migrar para `servico`, sem views de compatibilidade.
12. **Fotos oficiais do TSE** ficam guardadas e extraídas; a hospedagem pública segue a decisão do VPS (#30).

## Alternativas consideradas

- **Todo candidato em `pessoas`:** cria milhões de pessoas privadas que só concorreram, o que pesa na LGPD e contraria a regra de não ter página de pessoa privada.
- **Tabela única de eventos como fonte da verdade, com atributos soltos:** é o padrão EAV, sem tipo, sem teste e sem coluna descrita.
- **Só fatos tipados, sem `eventos`:** a linha do tempo seria um `UNION` reescrito em cada consulta e em cada aplicativo.
- **Continuar com marts por pergunta:** é a origem da dispersão atual.

## Consequências

- A migração é feita em fases (F1 a F6, issues próprias), cada uma com teste de reconciliação; nada é descartado de uma vez.
- Mudar nome de tabela em produção exige PR coordenado com os aplicativos.
- Vereadores entram em tudo (cerca de 58 mil eleitos por eleição municipal): custo de volume, não de complexidade.
- As referências de mercado do documento (Popolo, Open Civic Data, Wikidata P39, Kimball, Data Vault, bitemporal, EAV) foram citadas de memória e devem ser conferidas nas fontes.
- Ficam como issues: a escolha final de colunas de cada tabela (no PR de cada fase) e as fontes que faltam (diplomação #59, nomeações #19, tribunais #69).
