# Cobertura e lacunas

Para quem quer saber **o que o banco tem hoje, o que cada fonte ainda não entrega ao projeto e o que precisa vir de outras fontes**. Responde a três perguntas: o que vem de cada fonte (Câmara, Senado, TSE, legislação, emendas, IBGE), o que falta dela e de onde viria o resto. O catálogo das fontes (`fontes-de-dados.md`) diz **onde** está cada dado; este documento diz **o quanto** e **o que falta**.

Os números abaixo foram medidos no warehouse em 30/10/2026 (`dado-publico query`). Eles mudam a cada carga; `dado-publico observe` e `dado-publico coverage` mostram o estado atual.

## Números em 30/10/2026

| Medida | Valor |
| --- | --- |
| Pessoas do projeto (`dim_pessoas`) | 322.749 (todo eleito de qualquer cargo e todo parlamentar; ADR 0031) |
| Cadastro das casas (`dim_pessoas_cadastro`) | 7.889 da Câmara e 645 do Senado |
| Proposições | 886.573 da Câmara e 2.738 do Senado (as do Senado são as matérias votadas) |
| Proposições sem situação atual | 493.364 (a situação vem do detalhe por item, carregado por amostra) |
| Votações | 190.543 da Câmara, de 10/01/2000 a 28/10/2026, e 3.389 do Senado, de 09/03/1999 a 15/10/2026 |
| Votos individuais | 1.927.167 da Câmara e 273.094 do Senado |
| Autorias de proposições | 1.807.732 (só Câmara; o Senado não tem autorias, issue 14) |
| Tramitação da Câmara (amostra por item) | 479 andamentos |
| Legislaturas, partidos da Câmara | 58, 104 |
| Órgãos, participações em órgãos | 3.885, 94.630 |
| Frentes parlamentares, participações em frentes | 1.443, 262.015 |
| Normas, vetos | 244.021, 1.350 |
| Emendas parlamentares | 94.761 |
| Candidaturas (TSE, todos os cargos, eleições gerais e municipais de 1996 a 2026) | 3.685.373, das quais 930.375 de pessoas do projeto |
| Mandatos (um por candidatura eleita) e períodos de exercício | 534.032 e 6.275 (só Câmara e Senado) |

## Pendências de dados

O que falta no banco (histórico incompleto, tabelas que não existem, qualidade a resolver e melhorias da plataforma) fica nas [issues do repositório](https://github.com/codigo-publico-brasil/dado-publico-brasil/issues), com os rótulos `dados-historico`, `tabela-nova`, `qualidade` e `plataforma`. Dependências de decisão levam `decisao-do-fundador`; cargas longas, `carga-pesada`. As tabelas deste documento mostram o que há hoje; `dado-publico coverage` e `dado-publico observe` mostram os números atuais.

## 1. O que a Câmara entrega e o projeto já usa

| Dado | Fonte | Cobertura carregada |
| --- | --- | --- |
| Cadastro de deputados (nome, nome civil, sexo, nascimento, redes, site) | `deputados` | todos os deputados do arquivo, de todas as legislaturas |
| Profissões e ocupações declaradas | `deputadosProfissoes`, `deputadosOcupacoes` | arquivo completo |
| Proposições e situação atual | `proposicoes` | arquivos de 2000 a 2026 (cada arquivo traz proposições com datas de apresentação de vários anos; a regra de inclusão da fonte não foi confirmada) |
| Autoria de proposições | `proposicoesAutores` | mesmos anos |
| Votações (resultado e totais oficiais) | `votacoes` | 2000 a 2026 |
| Voto de cada deputado, com partido e UF na data | `votacoesVotos` | 2001 a 2026 |
| Orientação de bancada | `votacoesOrientacoes` | 2003 a 2026 |
| Proposições afetadas e objeto de cada votação | `votacoesProposicoes`, `votacoesObjetos` | 2000 a 2026 |
| Foto | arquivos de votos e de frentes (`deputado_urlFoto`) | quem votou ou esteve em frente |
| Legislaturas (datas oficiais) | `legislaturas` | todas |
| Partidos | `partidos` | todos |
| Órgãos e composição | `orgaos`, `orgaosDeputados` | todos os órgãos; composição das legislaturas 51 a 57 |
| Frentes parlamentares e participantes | `frentes`, `frentesDeputados` | arquivos completos |

## 2. O que a Câmara publica e o projeto ainda não carrega

| Dado | Por que importa | Observação |
| --- | --- | --- |
| Proposições anteriores a 2000 | histórico de decisões | a fonte cobre só alguns tipos antes de 2001; decidir o que mostrar |
| Mesas diretoras (`legislaturasMesas`) | quem presidiu a Casa | já coberta em parte pela composição do órgão `MESA` |
| Eventos e presenças | presença em sessões | volume grande; fora do primeiro entregável |
| Tramitação detalhada (histórico de situações) | hoje só há a **última** situação | exige o conjunto de tramitações ou a API |
| Temas e ementa detalhada | classificação por assunto | conjunto de temas da Câmara |
| Cota parlamentar (CEAP) | gastos | traz CPF e CNPJ de fornecedores: só entra com a minimização definida (o contrato recusa CPF) |
| Texto integral das proposições | leitura e resumo | links existem em `url_inteiro_teor`; o texto não é baixado |
| Início e fim do mandato **de cada pessoa** | mandato exato, com suplentes | a Câmara não publica em lote; o mart traz as datas oficiais da **legislatura** e os votos observados |

## Senado Federal: o que entra e o que falta

| Dado | Fonte | Cobertura carregada |
| --- | --- | --- |
| Senadores (nome, nome civil, sexo) e mandatos | `senadores` (por legislatura, 51 a 57) | todas as legislaturas desde 1999; mandatos e exercícios ficam no raw (`senadores__mandatos_mandato`) |
| Votações em plenário e voto de cada senador | `votacoes` (por ano) | 1999 a 2026 |
| Matérias votadas (sigla, ementa, apresentação, página oficial) | dentro das votações | só as que foram votadas |

Lacunas conhecidas, medidas ou registradas:

- **2015 e 2016 têm quase nenhuma votação** (17 e 13, contra cerca de 120 por ano nos demais). É o que a fonte devolve; a plataforma não completa.
- **Votação secreta** (1.782 das 3.389 votações e 96.075 dos 273.094 votos): a fonte não informa a escolha; o voto fica como `Votou`. `fct_votacoes.fl_votacao_secreta` marca essas votações.
- **Totais de Sim, Não e Abstenção** vêm vazios em parte das votações antigas. O teste `votacoes_com_total_sim_divergente` compara o total oficial com a contagem dos votos individuais, deixando de fora a votação secreta (não há Sim a contar): 13 votações, todas da Câmara.
- **Nascimento, naturalidade e foto** dos senadores não vêm do arquivo de legislatura, e sim do detalhe por senador (`senadores_detalhe`), carregado para os 843. Redes sociais não são carregadas.
- **Sem autoria nem situação das matérias**: exigem uma chamada por matéria; `brg_proposicoes_autorias` não tem autorias do Senado (issue 14), `situacao` fica vazia e `qtd_propostas` em `dim_pessoas_cadastro` é vazio (não zero) para senadores.
- **Siglas de partidos sem evento conferido** (teste `partidos_encerrados_sem_linhagem`, 3 em 27/10/2026, eram 5; a lista sai do próprio teste). Os casos são de três tipos: um partido que segue registrado no TSE e só ficou sem bancada na Câmara (a ocorrência é esperada); uma troca de nome deferida pelo TSE sem data da decisão encontrada (só se conhece o primeiro voto com a sigla nova); e uma sigla antiga cujos estatutos citados pelo TSE não batem com a mudança vista nos votos, sem data sustentada. Entraram em 27/10/2026 duas mudanças de nome, só com mês ou ano (as páginas do TSE responderam 403 e a data exata não foi conferida). A tabela só tem o que foi conferido numa página do TSE.
- **Mandato e exercício:** `fct_exercicios` traz o exercício real do Senado (titular e suplentes, com início, fim e causa de afastamento de cada período, como o Senado informa) e o da Câmara (a partir do histórico do deputado). `fct_mandatos` nasce da eleição, uma linha por candidatura eleita, e `app_cargo_ocupantes` junta os dois: o exercício onde há fonte e o mandato nos demais cargos.
- **Quem foi deputado e senador tem duas chaves de pessoa**: a regra conservadora liga só por identificador oficial da própria fonte, nunca por nome.

## Datasets por item (amostra)

Tramitação (Câmara) e processo (Senado) vêm por item, uma chamada para cada um, e **só rodam sob pedido** (`--foreach N`). Até a carga total ser pedida, o banco tem uma amostra dos itens mais recentes:

- **Câmara, tramitação:** só proposições que podem virar norma (PL, PLP, PEC, MPV, PDL, PLV, PLN e PRC: 96.134). Estão buscadas 300; o teste `proposicoes_alvo_sem_tramitacao` mede as que faltam, e `dado-publico coverage` mostra o quadro por dataset. A fonte não tem a norma resultante nesse endpoint: `normas_geradas` vem só do Senado por enquanto.
- **Senado, processo:** estão buscados 300 das 2.738 matérias votadas. Em metade das respostas (150) a fonte não informa `situacaoAtual`; fica vazia (nada é inferido). A autoria está no raw (`processos__autoria_iniciativa`) e o corpo completo no landing, mas ainda não nos marts, para não publicar contagens parciais por senador. A tramitação do Senado (`autuacoes`) está só no landing.
- **Câmara, histórico do deputado (#70):** carga completa de 26/10/2026, 7.889 deputados e 33.439 registros de status. Dá `dt_inicio` (primeiro registro em exercício) e `dt_fim` (registro de fim de mandato) em `fct_exercicios`. Lacunas: a legislatura 51 não tem histórico (0 de 556 mandatos com data); nas legislaturas 52 a 56 cerca de um quinto dos mandatos não tem registro de fim de mandato, e 21 mandatos da 57ª não têm registro em exercício, e ficam sem data (a fonte não informa; nada é inferido). Um caso (Bilac Pinto, 53ª) tem o fim de mandato antes da posse, como a fonte publica (`fct_exercicios` mantém o período como a fonte publica). No Senado, 21 mandatos (de pessoas sem nenhum exercício carregado) ficam só com a base "votos observados".
- **Auditoria:** `dado-publico verify` confere os hashes de todos os arquivos do landing e das respostas dentro dos lotes (landing íntegro na última conferência).

## TSE: candidaturas e ligação entre fontes

| Dado | Fonte | Cobertura carregada |
| --- | --- | --- |
| Candidaturas de todos os cargos, com partido, situação e resultado | `candidaturas` (um pacote por eleição) | eleições gerais e municipais de 1996 a 2026 (a de 1994 tem outro layout, issue 75); `DT_ELEICAO` por turno |

- **Ligação** por nome civil e nascimento iguais e únicos ([ADR 0013](../05-decisoes/0013-tse-ligacao-por-nome-civil-e-nascimento.md)) e a pessoa de todo eleito ([ADR 0031](../05-decisoes/0031-pessoas-de-todo-eleito.md)): 930.375 das 3.685.373 candidaturas são de pessoas do projeto (30/10/2026). As demais (quem nunca foi eleito) ficam em `fct_candidaturas` sem `id_pessoa`.
- **Eleitos ao Congresso sem vínculo:** 291 em 30/10/2026 (teste `eleitos_federais_sem_vinculo`). Em 24/10/2026 eram 398, com esta composição: 194 são da eleição de 2026 (outras 33 de 2002 e 22 de 2006 também sem registro digital), cujos eleitos ainda não tomaram posse (não há registro na Câmara nem no Senado, então não é falha de ligação); 130 têm alguém com a mesma data de nascimento mas nome civil diferente (candidatos à aprovação manual em `vinculos_aprovados`); 5 têm nome e data iguais a mais de um registro (homônimo); 34 não têm ninguém com a mesma data (por exemplo, eleitos de 1998 que não aparecem nas séries digitais).
- **Nascimento ausente:** 971 pessoas sem data de nascimento, o que impede a ligação por esta regra. O detalhe de todos os 843 senadores foi obtido; o que falta não vem na fonte.
- **Ambiguidade:** o teste `pessoas_ambiguas_entre_fontes` mede nome civil e nascimento repetidos dentro de uma fonte.
- **Resultado da eleição de 2026:** vem como a fonte informa na data da carga; uma eleição recente pode ter resultado ainda não consolidado.
- **Candidaturas sem voto (aviso):** 26 candidaturas de 2022 de pessoas do projeto não têm linha em `candidaturas_votos` (eram 56 antes de excluir vice-governador e vice-presidente, que não recebem voto próprio: o voto é do titular). As 26 são resultados em branco ou candidaturas sem voto na fonte.
- **Ainda não carregados:** redes sociais, fotos, certidões, coligações e vagas.

## Normas, vetos e Constituição

| O que | Dataset | Cobertura |
| --- | --- | --- |
| Catálogo das normas federais (metadados) | `normas` (por ano) | 1808 a 2026; só metadados |
| Publicações no Diário Oficial e relações com atos posteriores | `normas_detalhe` (por item) | leis, leis complementares, emendas e medidas provisórias (cerca de 25 mil), por amostra das mais recentes; a Constituição inteira em `normas_detalhe_constituicao` |
| Vetos | `vetos` (por ano) | 1994 a 2026 |
| Dispositivos vetados (texto, razão, situação) | `vetos_dispositivos` (por item) | por amostra dos vetos mais recentes |
| Voto nominal em dispositivo vetado | `vetos_votos` (por item) | por amostra; **não ligado a pessoas** |
| Constituição e ADCT, dispositivo a dispositivo | `constituicao`, `adct` | texto até a EC 141 e até a EC 136 |

Números de 23/10/2026: catálogo com **244.020 normas distintas** (as listas anuais da fonte repetem 511 entradas, que a carga junta pela chave); detalhe de 30 normas recentes e da Constituição; 1.350 vetos (1994 a 2026), com os dispositivos dos 126 mais recentes (1.256, dos quais 318 têm voto nominal na fonte) e o voto nominal de 20 desses dispositivos (9.696 votos); Constituição em 2.747 linhas e ADCT em 771.

Lacunas conhecidas, medidas ou registradas:

- **Catálogo:** 12 normas vêm sem o campo `tipo` e 103 sem ementa na própria fonte; ficam vazios (o teste `normas_sem_tipo` mede).
- **Texto das leis comuns:** não está na API documentada do Senado (ver o [catálogo de fontes](03-fontes-de-dados.md)). Hoje há só metadados e links; o texto virá de outra fonte, a decidir.
- **Vetos antes de 1994:** a API não devolve.
- **Voto nominal dos vetos sem código do parlamentar:** a fonte traz nome, partido e UF. A regra de ligação (ADR 0013) não liga só por nome, então esses votos ficam fora de `dim_pessoas`, com a fonte como está. Ligá-los exigiria uma regra nova, decidida em ADR.
- **Relações só das normas detalhadas:** o detalhe por norma vem por amostra; o teste `relacoes_de_norma_fora_do_catalogo` mede as que ainda não estão no catálogo (por exemplo, a Constituição enquanto 1988 não foi carregado).
- **Dispositivos votados sem voto carregado:** `dispositivos_votados_sem_votos_carregados` mede os dispositivos com voto nominal na fonte cujo voto ainda não foi buscado.
- **Constituição, emendas citadas:** o texto só cita a última emenda de cada trecho, então emendas que o Senado declara como alteração e o texto não cita são esperadas (13 em 23/10/2026). O inverso não pode acontecer: `emendas_do_texto_desconhecidas_do_senado` mede e `constituicao_cita_emenda_posterior_ao_arquivo` barra.
- **Leitura do HTML da Câmara:** o arquivo vem do Word, um parágrafo por dispositivo; o tipo e o contexto saem do começo de cada linha. Notas com erro de digitação na própria fonte ("nº 41, 2003") e com o parêntese de fechamento faltando foram tratadas; `constituicao_artigo_repetido` barra uma leitura que se perca.

## TSE complementar e emendas parlamentares

| O que | Dataset | Cobertura em 30/10/2026 |
| --- | --- | --- |
| Bens declarados pelos candidatos (todos os cargos) | `bens` (por eleição) | 2006 a 2026, gerais e municipais: 5.101.516 linhas no raw (30/10/2026) |
| Votos de cada candidato por município e zona (todos os cargos) | `votacao` (por eleição) | 1996 a 2026: 46.228.582 linhas no raw; o total por candidatura e turno está em `fct_resultados` (3.687.110 linhas) |
| Emendas parlamentares | `emendas` | 94.761 linhas (30/10/2026) |
| Convênios de emendas | `emendas_convenios` | 85.403 linhas |
| Quem recebeu o dinheiro, como o portal publica (com sinalização de dado pessoal) | `emendas_favorecidos` | 828.419 linhas, todas; `fl_contem_dado_pessoal` marca as de pessoa física e de CPF mascarado |

Lacunas conhecidas, medidas ou registradas:

- **Votos:** todos os anos de 1996 a 2026 estão no raw. Recarregar um ano é pesado (2022 sozinho levou 49 minutos): peça por ano, `--years ANO --dataset votacao`. Votos válidos de 2002 a 2014 são os nominais (issue 76).
- **Bens de 1998 e 2002:** a fonte não publica. Os de 2006 e 2010 usam outros nomes de coluna e entram por `aliases`. **Receitas e despesas de campanha** estão carregadas só para 2018, 2022 e 2026 (eleições gerais); as municipais e 2014 e antes estão na issue 150.
- **Candidaturas sem voto:** resultados em branco ou candidaturas sem votação na fonte; suplentes de senador e vices não têm voto próprio. O teste `candidaturas_sem_votos_carregados` saiu junto com o mart `candidaturas`; a candidatura sem resultado em `fct_resultados` é a medida.
- **Votos e bens de quem não é pessoa do projeto** (candidatos sem ligação): ficam no staging. Os eleitos de todos os cargos estão em `fct_mandatos`, e as campanhas, em `fct_candidaturas` e `app_pessoa_campanhas`.
- **Emenda sem ligação a pessoa:** o autor vem pelo nome e por um código orçamentário que não é o do parlamentar. 15.962 emendas (as antigas, sobretudo) vêm sem autor (`emendas_sem_autor_conhecido`).
- **Favorecido pessoa física:** entra como o portal publica, com CPF mascarado ([ADR 0017](../05-decisoes/0017-revisao-de-filtros-e-dados-pessoais.md)); a tabela, as colunas `favorecido` e `cd_favorecido` e cada linha (`fl_contem_dado_pessoal`) são sinalizadas como dado pessoal. Quem consome precisa tratar assim (LGPD).
- **Termos do portal:** o Termo de Uso do Portal da Transparência foi lido em 27/10/2026: permite a qualquer cidadão "visualizar e utilizar os dados disponíveis da forma que melhor lhe convier", sem definir licença, exigir citação nem restringir uso comercial, redistribuição ou acesso automatizado (detalhes em [fontes de dados](03-fontes-de-dados.md)). O dicionário de dados das emendas também foi lido (detalhes em [fontes de dados](03-fontes-de-dados.md)); vale a livre utilização do Decreto 8.777/2016.
- **Despesas (empenhos) e TCU:** não carregados. O DOU está só no landing, de ago a out de 2026 ([ADR 0019](../05-decisoes/0019-dou-so-no-landing.md)); o TCU não tem licença aberta (ver o [catálogo de fontes](03-fontes-de-dados.md)).

## Eleitos das eleições gerais

- **`eleitos`, `eleitos_cargos`, `eleitos_chapas`, `eleitos_historico` e `eleitos_campanhas` foram aposentados** ([ADR 0030](../05-decisoes/0030-modelo-de-dados-pessoa-no-centro.md)). Os eleitos e os mandatos, com a base (informada pelo TSE ou derivada), estão em `fct_mandatos`; quem ocupa o cargo em cada data, em `app_cargo_ocupantes` (exercício na Câmara e no Senado, mandato nos demais); as campanhas, em `app_pessoa_campanhas`. Os esquemas `core`, `fatos`, `analise` e `servico` e os marts antigos saíram no [ADR 0033](../05-decisoes/0033-marts-com-a-terminologia-da-dbt-labs.md). Vice e suplentes da chapa e a situação de vagas por cargo não têm substituto ainda.
- **Eleições suplementares e renovadas (#74), medido em 27/10/2026:** o TSE mistura, no mesmo arquivo, a eleição ordinária e as renovadas e suplementares do ano, cada uma com o seu `cd_eleicao` e com a descrição escrita de dezenas de jeitos (`Sup.`, `Suplem.`, `Nova Eleição`, `Majoritária - X`). O filtro por texto deixava passar parte delas: em 2012 havia 5.622 "vagas" de prefeito para 5.568 municípios e 54 municípios com dois eleitos. Agora, em cada ano, unidade, cargo e turno vale o código de eleição que cobre mais unidades (a ordinária cobre milhares; a suplementar, uma ou duas). Resultado: vagas de prefeito de 5.568 a 5.569 por eleição de 2012 a 2024, e nenhuma unidade com mais eleitos que vagas de 2004 a 2024. O que sobra de pendente é lacuna da fonte, sem palpite: unidades em que o arquivo não marca nenhum candidato como eleito (prefeito: 1 em 2012, 50 em 2016, 74 em 2020, 40 em 2024; vereador: 22 câmaras em 2024); só 0 a 4 por ano têm eleito numa eleição renovada. Em 2000 ainda há 30 prefeituras (todas só com 1º turno) e 125 câmaras com mais eleitos que vagas; no caso conferido (Bambuí) os dois eleitos têm o mesmo número e partido, o padrão de substituição de candidato, em que o arquivo antigo mantém os dois como eleitos; as demais não foram conferidas uma a uma. Em 1998 há duas unidades de deputado na mesma situação, sem causa conferida.
- **Campos de pessoas (#96, ADR 0029), medido em 27/10/2026:** `fct_candidaturas` ganhou nome social, grau de instrução, estado civil, ocupação, UF de nascimento, coligação e federação (declarados pelo candidato). Nos eleitos: grau de instrução 490.155, estado civil 490.034, ocupação 505.789, nome social 24 (quase ninguém declara). Federação só existe desde 2022. O TSE grava `Não divulgável` para candidatos com dado protegido (nome social 579, grau de instrução 17.659, estado civil 14.283, ocupação 1.701 linhas) e às vezes repete o nome civil no nome social (468 de 640); os dois casos ficam como a fonte informa. Cor ou raça não entra. Em `dim_pessoas_cadastro`: escolaridade de 5.791 dos 7.889 deputados; contato do gabinete dos 513 deputados atuais (a Câmara não publica o dos antigos); no Senado, e-mail de 241, endereço de 155, telefone de 42 e página oficial de 275 de 646.
- **Votações do Senado com data errada na fonte (#100):** 36 das 3.374 votações (2.913 votos) saem com datas impossíveis; por exemplo, a PEC 15/1998 vem com `dataSessao` de 01/04/2015 e 81 senadores de 1999 a 2003 (conferido na API em 27/10/2026). Os votos ficam como a fonte publica e o teste `votacoes_do_senado_com_data_suspeita` as mede. Para quem tem exercício oficial, o mandato do Senado só existe nas legislaturas desses exercícios (203 mandatos falsos deixaram de ser criados; de 989 para 786). A fonte precisa corrigir a data; a plataforma não a corrige.
- **Ainda não carregados:** a prestação de contas das eleições municipais e de 2014 e antes (issue 150) e as fotos municipais (issue 177); as propostas de governo (issue 95) e a diplomação (issue 59), que não vêm nos arquivos abertos. As eleições municipais, vices e suplentes já estão carregados. A data de posse dos deputados estaduais e distritais depende das constituições estaduais (issue 173), e o exercício real fora da Câmara e do Senado é a issue 162.

## 3. O que a Câmara **não** tem e precisa vir de outra instância

| Necessidade | Fonte provável | Por que a Câmara não basta |
| --- | --- | --- |
| Senadores, votos e matérias do Senado | Senado Federal, dados abertos | outra casa legislativa |
| Presidente, vice e ministros | TSE (candidaturas e eleitos), Planalto, DOU | pertencem ao Executivo |
| Candidaturas, eleições e resultados | TSE | a Câmara só conhece quem tomou posse |
| Filiação partidária por período | TSE | a Câmara só informa o partido **na data do voto**; mudanças de nome, fusões e incorporações dos partidos estão em `dim_partidos_linhagem` (curada, só o que foi conferido no TSE; faltam as siglas medidas por `partidos_encerrados_sem_linhagem`) |
| Lei, decreto ou medida provisória que resultou da proposição | Diário Oficial da União, API de legislação do Senado | a Câmara termina no trâmite; a norma publicada é outro documento (o catálogo de normas já está em `fct_normas`; falta ligar as proposições da Câmara) |
| Sanção, veto e derrubada de veto | Senado/Congresso, DOU | acontecem depois da votação na Câmara (vetos desde 1994 em `fct_vetos` e `fct_vetos_dispositivos`) |
| Emendas parlamentares e dinheiro público | Portal da Transparência, TCU | outro assunto (emendas já em `fct_emendas`; despesas e TCU não) |
| Município de São Paulo | Câmara Municipal, Querido Diário | outro ente |
| Decisões anteriores às séries digitais | curadoria manual, rotulada | não há dado estruturado |

## 4. Limitações do carregamento atual

- **Foto só para quem votou ou esteve em frente parlamentar.** O cadastro não traz foto; ela vem dos arquivos de votos e de frentes. Quem não aparece neles fica "sem foto"; o teste `pessoas_sem_foto` mede a lacuna.
- **Mandato e exercício.** `fct_mandatos` tem o início derivado da Constituição (`base_dt_inicio`) e o fim previsto pela duração do cargo; o exercício real (licença, suplente, causa do fim) só existe para a Câmara e o Senado, em `fct_exercicios`. Ver [identidade de pessoas](../01-entender/05-identidade-de-pessoas.md).
- **Órgãos citados e ausentes da lista de órgãos.** A composição cita 129 órgãos (como o Congresso Nacional e comissões especiais) que o arquivo de órgãos da Câmara não lista. As participações ficam, com a sigla informada na própria linha, e o teste de relação do dbt mede a lacuna.
- **Participações em frentes sem deputado.** 256 linhas de coordenação antiga não identificam o deputado; ficam no staging e saem dos marts.
- **Linhas repetidas com `dataFim` diferente.** Na composição de órgãos, a fonte traz às vezes a mesma participação duas vezes, uma aberta e outra encerrada. As duas são mantidas (o raw identifica a linha pelo conteúdo, `_row_hash`); quem consome deve considerar a encerrada.
- **Referências a proposições de anos não carregados.** Votações e autorias podem citar proposições de anos que não foram baixados. Elas aparecem como "ano ainda não carregado", com o link para a ficha oficial, sem inventar dados. Testes `autoria_de_proposicao_nao_carregada` e `votacao_de_proposicao_nao_carregada` contam os casos.
- **Muitas proposições sem situação.** Nos arquivos da Câmara, uma parte grande das proposições vem sem a última situação (493.364 em 30/10/2026). O campo fica vazio e o aplicativo mostra a lacuna; o teste `proposicoes_sem_situacao` a mede.
- **Divergência entre fontes oficiais.** A data de falecimento de um deputado consta no arquivo em lote e não na API de detalhe. As duas fontes são oficiais; o projeto usa o arquivo em lote e registra a divergência.
- **O `merge` do dlt não apaga.** Se a Câmara remover uma linha de um arquivo, o raw mantém a linha antiga. O landing guarda os dois arquivos e o aviso `linhas_removidas` (`dado-publico observe`) conta as linhas de capturas anteriores que a atual não traz.
- **Siglas em ementas.** A lista de siglas para preservar a caixa é aprendida de todas as ementas de caixa mista carregadas (modelo `int_ementas_siglas_extraidas`, mínimo de 3 ocorrências). Uma sigla que só apareça em ementas de caixa alta pode ser minusculizada.

## 5. Onde estão os números atuais

| Pergunta | Onde ver |
| --- | --- |
| Quantas linhas há em cada tabela e quanto de cada coluna está preenchido | `dado-publico query` e `dado-publico coverage` |
| Quais testes de dados falharam ou mediram lacuna | `dado-publico observe` (resumo) ou o relatório HTML do Elementary |
| Há quanto tempo cada arquivo foi verificado | `metadata.captures` (`last_checked_at`) e o `observe` |
| Quais valores existem em colunas como `voto` e `situacao` | `dado-publico query --sql "select voto, count(*) from marts.fct_votos group by 1"` |
