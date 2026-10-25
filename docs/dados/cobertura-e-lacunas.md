# Cobertura e lacunas

Para quem quer saber **o que o banco tem hoje, o que a Câmara ainda não entrega ao projeto e o que precisa vir de outras fontes**. Responde a três perguntas: o que vem da Câmara, o que falta dela, e de onde viria o resto. O catálogo das fontes (`fontes-de-dados.md`) diz o que cada fonte oferece; este documento diz o que já foi carregado e o que sobra.

Os números abaixo são da carga histórica de 21/10/2026 (Câmara: `run --historical --from-year 2000`; Senado: `run --historical --from-year 1999 --source senado`). Eles mudam a cada carga; a página `/qualidade` do explorador mostra os atuais.

## Números da carga de 21/10/2026

| Medida | Valor |
| --- | --- |
| Pessoas (Câmara) | 7.889 (887 só aparecem nos votos, sem cadastro) |
| Proposições (Câmara) | 885.777 |
| Votações (Câmara) | 190.401, de 10/01/2000 a 15/10/2026 |
| Votações sem nenhum voto individual (simbólicas ou sem registro) | 184.362 |
| Votos individuais (Câmara) | 1.927.167 |
| Proposições sem situação atual | 489.694 |
| Pessoas sem foto | 5.682 |
| Autorias de pessoas em proposições não carregadas | 11.257 |
| Ligações votação-proposição de proposições não carregadas | 6.158 |
| Legislaturas, partidos | 58, 104 |
| Órgãos, participações em órgãos | 3.883, 94.616 |
| Frentes parlamentares, participações em frentes | 1.443, 262.014 |
| Participações em órgãos de órgão ausente da lista de órgãos da fonte | 6.409 (129 órgãos, como o Congresso Nacional e comissões especiais) |
| Participações em frentes sem deputado identificado pela fonte | 256 (coordenações antigas) |
| Pessoas, votações, votos e matérias do **Senado** | 864, 3.389 (de 1999 a 2026), 273.094 e 2.738 |
| Mandatos (votos observados) do Senado | 989 |
| Tramitação da Câmara (amostra por item: os 300 mais recentes dos 96.134 alvos) | 300 proposições, 338 andamentos |
| Processos do Senado (amostra por item: 300 das 2.738 matérias votadas) | 300 processos, 75 normas geradas |
| Pessoas hoje (depois da fusão deputado e senador) | 8.535, das quais 218 estão nas duas casas |
| Candidaturas no TSE (eleições gerais de 1998 a 2026, todos os cargos; medido em 24/10/2026) | 180.970 no staging; 10.997 candidaturas de 3.201 pessoas do projeto no mart |
| Diário Oficial da União (landing, ago a out de 2026) | 9 zips, 620 MB, sem tabelas |
| Detalhe de senadores (nascimento, naturalidade, foto) | 843 de 843 buscados |
| Testes do dbt do tipo erro que falharam | 0 |

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
- **Votação secreta** (1.782 das 3.389 votações e 96.075 dos 273.094 votos): a fonte não informa a escolha; o voto fica como `Votou`. `marts.votacoes.votacao_secreta` marca essas votações.
- **Totais de Sim, Não e Abstenção** vêm vazios em parte das votações antigas. O teste `votacoes_com_total_sim_divergente` compara o total oficial com a contagem dos votos individuais, deixando de fora a votação secreta (não há Sim a contar): 13 votações, todas da Câmara.
- **Sem nascimento, foto e redes** dos senadores: o arquivo de legislatura não as traz.
- **Sem autoria nem situação das matérias**: exigem uma chamada por matéria; `proposicoes_autorias` e `situacao` ficam vazios para o Senado, e `pessoas.qtd_propostas` é vazio (não zero) para senadores.
- **Siglas de partidos sem evento conferido** (teste `partidos_encerrados_sem_linhagem`, 5 em 2026-10-23): PRTB, PSDC (o TSE deferiu a troca para Democracia Cristã, mas a data da decisão não foi encontrada), PTC, SD e SDD. A tabela só tem o que foi conferido numa página do TSE.
- **Mandatos oficiais:** `marts.mandatos_exercicios` traz titular e suplentes do Senado, com início, fim e causa de afastamento de cada período, como o Senado informa. `marts.mandatos` continua vindo dos votos observados, nas duas casas; a Câmara não publica o exercício.
- **Quem foi deputado e senador tem duas chaves de pessoa**: a regra conservadora liga só por identificador oficial da própria fonte, nunca por nome.

## Datasets por item (amostra)

Tramitação (Câmara) e processo (Senado) vêm por item, uma chamada para cada um, e **só rodam sob pedido** (`--foreach N`). Até a carga total ser pedida, o banco tem uma amostra dos itens mais recentes:

- **Câmara, tramitação:** só proposições que podem virar norma (PL, PLP, PEC, MPV, PDL, PLV, PLN e PRC: 96.134). Estão buscadas 300; o teste `proposicoes_alvo_sem_tramitacao` mede as que faltam, e `dado-publico coverage` mostra o quadro por dataset. A fonte não tem a norma resultante nesse endpoint: `normas_geradas` vem só do Senado por enquanto.
- **Senado, processo:** estão buscados 300 das 2.738 matérias votadas. Em metade das respostas (150) a fonte não informa `situacaoAtual`; fica vazia (nada é inferido). A autoria está no raw (`processos__autoria_iniciativa`) e o corpo completo no landing, mas ainda não nos marts, para não publicar contagens parciais por senador. A tramitação do Senado (`autuacoes`) está só no landing.
- **Auditoria:** `dado-publico verify` confere os hashes de todos os arquivos do landing e das respostas dentro dos lotes (landing íntegro na última conferência).

## TSE: candidaturas e ligação entre fontes

| Dado | Fonte | Cobertura carregada |
| --- | --- | --- |
| Candidaturas de todos os cargos, com partido, situação e resultado | `candidaturas` (um pacote por eleição) | eleições gerais de 1998, 2002, 2006, 2010, 2014, 2018, 2022 e 2026 |

- **Ligação** por nome civil e nascimento iguais e únicos ([ADR 0013](../adr/0013-tse-ligacao-por-nome-civil-e-nascimento.md)): 10.790 candidaturas ligadas (10.997 linhas no mart, 3.201 pessoas). As demais (candidatos de fora do Congresso e quem não foi eleito) ficam no staging.
- **Eleitos sem vínculo:** 398 candidaturas marcadas como eleitas não foram ligadas (teste `eleitos_federais_sem_vinculo`). Medido em 2026-10-24: 194 são da eleição de 2026 (outras 33 de 2002 e 22 de 2006 também sem registro digital), cujos eleitos ainda não tomaram posse (não há registro na Câmara nem no Senado, então não é falha de ligação); 130 têm alguém com a mesma data de nascimento mas nome civil diferente (candidatos à aprovação manual em `vinculos_aprovados`); 5 têm nome e data iguais a mais de um registro (homônimo); 34 não têm ninguém com a mesma data (por exemplo, eleitos de 1998 que não aparecem nas séries digitais).
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
- **Texto das leis comuns:** não está na API documentada do Senado (ver o [catálogo de fontes](fontes-de-dados.md)). Hoje há só metadados e links; o texto virá de outra fonte, a decidir.
- **Vetos antes de 1994:** a API não devolve.
- **Voto nominal dos vetos sem código do parlamentar:** a fonte traz nome, partido e UF. A regra de ligação (ADR 0013) não liga só por nome, então esses votos ficam fora de `pessoas`, com a fonte como está. Ligá-los exigiria uma regra nova, decidida em ADR.
- **Relações só das normas detalhadas:** o detalhe por norma vem por amostra; o teste `relacoes_de_norma_fora_do_catalogo` mede as que ainda não estão no catálogo (por exemplo, a Constituição enquanto 1988 não foi carregado).
- **Dispositivos votados sem voto carregado:** `dispositivos_votados_sem_votos_carregados` mede os dispositivos com voto nominal na fonte cujo voto ainda não foi buscado.
- **Constituição, emendas citadas:** o texto só cita a última emenda de cada trecho, então emendas que o Senado declara como alteração e o texto não cita são esperadas (13 em 23/10/2026). O inverso não pode acontecer: `emendas_do_texto_desconhecidas_do_senado` mede e `constituicao_cita_emenda_posterior_ao_arquivo` barra.
- **Leitura do HTML da Câmara:** o arquivo vem do Word, um parágrafo por dispositivo; o tipo e o contexto saem do começo de cada linha. Notas com erro de digitação na própria fonte ("nº 41, 2003") e com o parêntese de fechamento faltando foram tratadas; `constituicao_artigo_repetido` barra uma leitura que se perca.

## TSE complementar e emendas parlamentares

| O que | Dataset | Cobertura em 23/10/2026 |
| --- | --- | --- |
| Bens declarados pelos candidatos (todos os cargos) | `bens` (por eleição) | 2006, 2010, 2014, 2018, 2022 e 2026: 510.172 bens no raw; 92.242 nos marts (2.682 pessoas, 7.584 candidaturas); medido em 24/10/2026 |
| Votos de cada candidato por município e zona (todos os cargos) | `votacao` (por eleição) | **só 2022**: 9.377.845 linhas e 26.237 candidaturas no raw; 1.221 linhas de 1.206 pessoas do projeto nos marts |
| Emendas parlamentares | `emendas` | 94.736 linhas, de 2014 a 2026 |
| Convênios de emendas | `emendas_convenios` | 85.403 linhas |
| Quem recebeu o dinheiro, como o portal publica (com sinalização de dado pessoal) | `emendas_favorecidos` | 828.419 linhas, todas; `fl_contem_dado_pessoal` marca as de pessoa física e de CPF mascarado |

Lacunas conhecidas, medidas ou registradas:

- **Votos de 1998 a 2018:** não carregados (2,4 GB compactados no total; 2022 sozinho levou 49 minutos para entrar no raw). Pedir por ano: `--years ANO --dataset votacao`.
- **Bens de 1998 e 2002:** a fonte não publica. Os de 2006 e 2010 usam outros nomes de coluna e entram por `aliases`.
- **Candidaturas sem voto** (`candidaturas_sem_votos_carregados`, 26 em 2022): resultados em branco ou candidaturas sem votação na fonte. Suplentes de senador e vices não têm voto próprio e ficam de fora do teste.
- **Votos e bens de quem não é pessoa do projeto** (candidatos sem ligação): ficam no staging. Os eleitos entram em `eleitos` e `eleitos_campanhas` mesmo sem ligação, inclusive os deputados estaduais e distritais.
- **Emenda sem ligação a pessoa:** o autor vem pelo nome e por um código orçamentário que não é o do parlamentar. 15.962 emendas (as antigas, sobretudo) vêm sem autor (`emendas_sem_autor_conhecido`).
- **Favorecido pessoa física:** entra como o portal publica, com CPF mascarado ([ADR 0017](../adr/0017-revisao-de-filtros-e-dados-pessoais.md)); a tabela, as colunas `favorecido` e `cd_favorecido` e cada linha (`fl_contem_dado_pessoal`) são sinalizadas como dado pessoal. Quem consome precisa tratar assim (LGPD).
- **Termos do portal:** as páginas de termos de uso e de dicionário de dados do Portal da Transparência pedem verificação anti-robô e não foram lidas; vale a licença de livre utilização do Decreto 8.777/2016.
- **Despesas (empenhos) e TCU:** não carregados. O DOU está só no landing, de ago a out de 2026 ([ADR 0019](../adr/0019-dou-so-no-landing.md)); o TCU não tem licença aberta (ver o [catálogo de fontes](fontes-de-dados.md)).

## Eleitos das eleições gerais

| O que | Mart | Cobertura em 25/10/2026 |
| --- | --- | --- |
| Eleitos de todos os cargos (presidente, governador, senador, deputados, prefeito e vereador) | `eleitos` | 1998 a 2026, das candidaturas carregadas (resultado como o TSE informa; provisório até a diplomação) |
| Situação de cada cargo (vagas, eleitos e pendentes) | `eleitos_cargos` | 2022 e 2026 (as vagas só foram carregadas desses anos) |
| Totais de bens, receitas e despesas de cada eleito | `eleitos_campanhas` | bens de 2006 em diante; receitas e despesas de 2026 (190.178 receitas e 1.111.628 despesas, todas as linhas do TSE). Vazio, e não zero, quando o arquivo não traz o candidato |

- **2026, pelo arquivo de candidaturas de 21/10:** 513 de 513 deputados federais eleitos (335 já ligados a pessoa: 305 reeleitos, 26 retornos e 182 novatos), 52 de 54 senadores, 20 de 27 governadores (7 aguardam o 2º turno) e a presidência aguardando o 2º turno. O resultado muda a cada captura do TSE.
- **Fila de revisão:** `eleitos_com_possivel_vinculo` lista os eleitos ao Congresso sem vínculo que têm alguém com a mesma data de nascimento na base; uma pessoa confere e aprova em `vinculos_aprovados`.
- **Ainda não carregados:** a prestação de contas de 2022 e de anos anteriores (carga pesada, só quando pedida); as propostas de governo e a diplomação, que não vêm nos arquivos abertos; as eleições municipais, vices e suplentes (issues 62, 63 e 64).

## 3. O que a Câmara **não** tem e precisa vir de outra instância

| Necessidade | Fonte provável | Por que a Câmara não basta |
| --- | --- | --- |
| Senadores, votos e matérias do Senado | Senado Federal, dados abertos | outra casa legislativa |
| Presidente, vice e ministros | TSE (candidaturas e eleitos), Planalto, DOU | pertencem ao Executivo |
| Candidaturas, eleições e resultados | TSE | a Câmara só conhece quem tomou posse |
| Filiação partidária por período | TSE | a Câmara só informa o partido **na data do voto**; mudanças de nome, fusões e incorporações dos partidos estão em `marts.partidos_linhagem` (curada, só o que foi conferido no TSE; faltam as siglas medidas por `partidos_encerrados_sem_linhagem`) |
| Lei, decreto ou medida provisória que resultou da proposição | Diário Oficial da União, API de legislação do Senado | a Câmara termina no trâmite; a norma publicada é outro documento (o catálogo de normas já está em `marts.normas`; falta ligar as proposições da Câmara) |
| Sanção, veto e derrubada de veto | Senado/Congresso, DOU | acontecem depois da votação na Câmara (vetos desde 1994 em `marts.vetos` e `marts.vetos_dispositivos`) |
| Emendas parlamentares e dinheiro público | Portal da Transparência, TCU | outro assunto (emendas já em `marts.emendas`; despesas e TCU não) |
| Município de São Paulo | Câmara Municipal, Querido Diário | outro ente |
| Decisões anteriores às séries digitais | curadoria manual, rotulada | não há dado estruturado |

## 4. Limitações do carregamento atual

- **Foto só para quem votou ou esteve em frente parlamentar.** O cadastro não traz foto; ela vem dos arquivos de votos e de frentes. Quem não aparece neles fica "sem foto"; o teste `pessoas_sem_foto` mede a lacuna.
- **Mandato por votos observados.** Início e fim do mandato de cada pessoa ficam vazios, porque a fonte não os publica em lote (suplentes entram e saem no meio da legislatura). O mart traz, ao lado, as datas oficiais da legislatura (`dt_legislatura_inicio`, `dt_legislatura_fim`), que **não** são as do mandato (ver [identidade de pessoas](identidade-de-pessoas.md)).
- **Órgãos citados e ausentes da lista de órgãos.** A composição cita 129 órgãos (como o Congresso Nacional e comissões especiais) que `orgaos.csv` não lista. As participações ficam, com a sigla informada na própria linha, e o teste de relação do dbt mede a lacuna.
- **Participações em frentes sem deputado.** 256 linhas de coordenação antiga não identificam o deputado; ficam no staging e saem dos marts.
- **Linhas repetidas com `dataFim` diferente.** Na composição de órgãos, a fonte traz às vezes a mesma participação duas vezes, uma aberta e outra encerrada. As duas são mantidas (o raw identifica a linha pelo conteúdo, `_row_hash`); quem consome deve considerar a encerrada.
- **Referências a proposições de anos não carregados.** Votações e autorias podem citar proposições de anos que não foram baixados. Elas aparecem como "ano ainda não carregado", com o link para a ficha oficial, sem inventar dados. Testes `autoria_de_proposicao_nao_carregada` e `votacao_de_proposicao_nao_carregada` contam os casos.
- **Muitas proposições sem situação.** Nos arquivos da Câmara, uma parte grande das proposições vem sem a última situação. A página mostra o campo vazio.
- **Divergência entre fontes oficiais.** A data de falecimento de um deputado consta no arquivo em lote e não na API de detalhe. As duas fontes são oficiais; o projeto usa o arquivo em lote e registra a divergência.
- **O `merge` do dlt não apaga.** Se a Câmara remover uma linha de um arquivo, o raw mantém a linha antiga. O landing guarda os dois arquivos e o aviso `linhas_removidas` (`dado-publico observe`) conta as linhas de capturas anteriores que a atual não traz.
- **Siglas em ementas.** A lista de siglas para preservar a caixa é aprendida de todas as ementas de caixa mista carregadas (modelo `int_ementas_siglas_extraidas`, mínimo de 3 ocorrências). Uma sigla que só apareça em ementas de caixa alta pode ser minusculizada.

## 5. Onde estão os números atuais

| Pergunta | Onde ver |
| --- | --- |
| Quantas linhas há em cada tabela e quanto de cada coluna está preenchido | `/qualidade` do explorador |
| Quais testes de dados falharam ou mediram lacuna | `/qualidade`, seção "Testes de dados" |
| Há quanto tempo cada arquivo foi verificado | `/qualidade`, seção "Frescor das capturas" |
| Quais valores existem em colunas como `voto` e `situacao` | `/qualidade`, "Valores de colunas categóricas" |
