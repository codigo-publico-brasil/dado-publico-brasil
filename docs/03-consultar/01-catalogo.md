# Catálogo de dados

Gerado do projeto dbt (`dado-publico catalog`). Não edite à mão: edite a descrição e o `meta` do modelo ou da fonte e gere de novo.

## raw_federal_camara

| Tabela | O que é | Sensibilidade | Grain |
| --- | --- | --- | --- |
| `deputados` | Cadastro de deputados (sem documentos pessoais). | publico-agente-publico |  |
| `deputados_detalhe` | Cadastro de cada deputado (escolaridade, último status e gabinete institucional), buscado por item na API (`_item` é o endereço do deputado), só dos que já foram buscados. | publico-agente-publico |  |
| `deputados_historico` | Histórico de situação de cada deputado (posse, licença, fim de mandato), buscado por item na API (`_item` é o endereço do deputado), só dos que já foram buscados. | publico-agente-publico |  |
| `deputados_ocupacoes` | Ocupações anteriores declaradas pelos deputados (arquivo completo). | publico-agente-publico |  |
| `deputados_profissoes` | Profissões declaradas pelos deputados (arquivo completo, substituído a cada carga). | publico-agente-publico |  |
| `frentes` | Frentes parlamentares, com legislatura de criação e coordenador. | publico-agente-publico |  |
| `frentes_deputados` | Deputados em cada frente parlamentar, com o título (coordenador, membro) na legislatura. | publico-agente-publico |  |
| `legislaturas` | Legislaturas da Câmara, com início, fim e ano da eleição. | publico-agente-publico |  |
| `orgaos` | Órgãos da Câmara (comissões, plenário, mesa, conselhos), com tipo e situação. | publico-agente-publico |  |
| `orgaos_deputados` | Deputados em cada órgão, com cargo e período, um arquivo por legislatura. | publico-agente-publico |  |
| `partidos` | Partidos com sigla e nome. | publico-agente-publico |  |
| `proposicoes` | Proposições, um arquivo por ano, com a última situação. | publico-agente-publico |  |
| `proposicoes_autores` | Autores de cada proposição (pessoa ou órgão), na ordem de assinatura. | publico-agente-publico |  |
| `proposicoes_tramitacoes` | Tramitação das proposições que podem virar norma, buscada por item na API (`_item` é o id da proposição), só das que já foram buscadas. | publico-agente-publico |  |
| `votacoes` | Votações com resultado e totais oficiais. | publico-agente-publico |  |
| `votacoes_objetos` | Proposições que são objeto de cada votação. | publico-agente-publico |  |
| `votacoes_orientacoes` | Orientação de cada bancada em cada votação. | publico-agente-publico |  |
| `votacoes_proposicoes` | Proposições afetadas por cada votação. | publico-agente-publico |  |
| `votacoes_votos` | Voto de cada deputado em cada votação nominal, com partido e UF na data. | publico-agente-publico |  |

## raw_federal_constituicao

| Tabela | O que é | Sensibilidade | Grain |
| --- | --- | --- | --- |
| `adct` | Ato das Disposições Constitucionais Transitórias, uma linha por parágrafo do arquivo. | publico |  |
| `constituicao` | Texto da Constituição (parte permanente), uma linha por parágrafo do arquivo. | publico |  |

## raw_federal_ibge

| Tabela | O que é | Sensibilidade | Grain |
| --- | --- | --- | --- |
| `municipios` | Municípios do Brasil, uma linha por município, com a hierarquia regional imediata e intermediária. | publico |  |

## raw_federal_senado

| Tabela | O que é | Sensibilidade | Grain |
| --- | --- | --- | --- |
| `normas` | Catálogo das normas federais (leis, decretos, medidas provisórias, emendas...), por ano de assinatura, só os metadados. | publico-agente-publico |  |
| `normas_detalhe` | Detalhe, buscado por item na API, das leis, leis complementares, emendas e medidas provisórias já buscadas (`_item` é o código da norma). | publico-agente-publico |  |
| `normas_detalhe__publicacoes_publicacao` | Publicações de cada norma no Diário Oficial (lista `publicacoes.publicacao`). | publico-agente-publico |  |
| `normas_detalhe__vides_vide` | Relações de cada norma com atos posteriores (alteração, regulamentação, veto; lista `vides.vide`). | publico-agente-publico |  |
| `normas_detalhe__vides_vide__itens__item` | Dispositivos da norma a que cada relação se refere (lista `itens.item` de cada vide). | publico-agente-publico |  |
| `normas_detalhe_constituicao` | Detalhe da Constituição de 1988 (norma 579494), um documento só. | publico-agente-publico |  |
| `normas_detalhe_constituicao__publicacoes_publicacao` | Publicações da Constituição no Diário Oficial. | publico-agente-publico |  |
| `normas_detalhe_constituicao__vides_vide` | Relações da Constituição com atos posteriores (quem a alterou, regulamentou e interpretou). | publico-agente-publico |  |
| `normas_detalhe_constituicao__vides_vide__itens__item` | Dispositivos da Constituição a que cada relação se refere (lista `itens.item` de cada vide). | publico-agente-publico |  |
| `processos` | Processo de cada matéria votada, buscado por item na API (`_item` é o id do processo), só das já buscadas: situação atual e norma gerada. | publico-agente-publico |  |
| `processos__autoria_iniciativa` | Autoria de cada processo (lista `autoriaIniciativa`). | publico-agente-publico |  |
| `senadores` | Senadores por legislatura (o mesmo senador aparece em várias), com os mandatos em tabelas filhas. | publico-agente-publico |  |
| `senadores__mandatos_mandato` | Mandatos de cada senador na legislatura (titular ou suplente), lista `Mandatos.Mandato`. | publico-agente-publico |  |
| `senadores__mandatos_mandato__exercicios__exercicio` | Períodos de exercício de cada mandato, com a causa de afastamento (lista `Exercicios.Exercicio`). | publico-agente-publico |  |
| `senadores_detalhe` | Detalhe de cada senador, buscado por item na API (`_item` é o código do senador): nascimento, naturalidade e foto, páginas oficiais e contato institucional do gabinete, só dos já buscados. | publico-agente-publico |  |
| `senadores_detalhe__telefones_telefone` | Telefones do gabinete de cada senador (lista `Telefones` do detalhe), uma linha por telefone. | publico-agente-publico |  |
| `vetos` | Vetos presidenciais apreciados pelo Congresso, por ano, de 1994 em diante. | publico-agente-publico |  |
| `vetos_dispositivos` | Dispositivos vetados de cada veto, buscados por item (`_item` é o código da matéria do veto), com razão do veto e situação. | publico-agente-publico |  |
| `vetos_votos` | Voto nominal em cada dispositivo votado em painel, buscado por item (`_item` é o código do dispositivo). | publico-agente-publico |  |
| `vetos_votos__camara_voto` | Votos dos deputados no dispositivo (nome, partido, UF e voto, sem código do parlamentar). | publico-agente-publico |  |
| `vetos_votos__senado_voto` | Votos dos senadores no dispositivo (nome, partido, UF e voto, sem código do parlamentar). | publico-agente-publico |  |
| `votacoes` | Votações em plenário com resultado, totais e a matéria votada. | publico-agente-publico |  |
| `votacoes__votos` | Voto de cada senador em cada votação nominal (lista `votos` da votação). | publico-agente-publico |  |

## raw_federal_transparencia

| Tabela | O que é | Sensibilidade | Grain |
| --- | --- | --- | --- |
| `compras` | Contratos do governo federal, um por linha (o contratado pessoa física traz CPF completo). Fonte: saida/compras/AAAAMM_Compras.zip. | publico-dados-pessoais-de-terceiros |  |
| `compras_itens` | Itens dos contratos do governo federal. | publico-dados-pessoais-de-terceiros |  |
| `compras_termos_aditivos` | Termos aditivos dos contratos do governo federal. | publico-dados-pessoais-de-terceiros |  |
| `despesas` | Execução da despesa federal por mês, órgão, unidade gestora, ação e natureza da despesa (sem favorecido). Fonte: saida/despesas-execucao/AAAAMM_Despesas.zip. | publico-dados-pessoais-de-terceiros |  |
| `emendas` | Emendas parlamentares por localidade, função, programa e ação, com os valores empenhado, liquidado e pago. | publico-dados-pessoais-de-terceiros |  |
| `emendas_convenios` | Convênios firmados com recursos de emendas parlamentares. | publico-dados-pessoais-de-terceiros |  |
| `emendas_favorecidos` | Quem recebeu o dinheiro das emendas, como a fonte publica (inclui pessoa física, com CPF mascarado). | publico-dados-pessoais-de-terceiros |  |
| `licitacoes` | Licitações do governo federal (SIASG), uma por linha. Fonte: saida/licitacoes/AAAAMM_Licitacoes.zip, membro AAAAMM_Licitação.csv. | publico-dados-pessoais-de-terceiros |  |
| `licitacoes_empenhos` | Empenhos relacionados às licitações. Mesmo zip, membro AAAAMM_EmpenhosRelacionados.csv. | publico-dados-pessoais-de-terceiros |  |
| `licitacoes_itens` | Itens das licitações, com o vencedor (CPF completo se pessoa física). Mesmo zip, membro AAAAMM_ItemLicitação.csv. | publico-dados-pessoais-de-terceiros |  |
| `licitacoes_participantes` | Participantes dos itens das licitações (CPF completo se pessoa física). Mesmo zip, membro AAAAMM_ParticipantesLicitação.csv. | publico-dados-pessoais-de-terceiros |  |

## raw_federal_tse

| Tabela | O que é | Sensibilidade | Grain |
| --- | --- | --- | --- |
| `bens` | Bens declarados pelos candidatos de todos os cargos nas eleições gerais de 2006 em diante, uma linha por bem. | publico-agente-publico |  |
| `candidaturas` | Candidaturas a deputado federal e senador (e suplentes) nas eleições gerais, uma linha por candidatura. | publico-agente-publico |  |
| `despesas_candidatos` | Despesas contratadas declaradas na prestação de contas dos candidatos de todos os cargos, uma linha por despesa, só com as colunas do total (sem nome nem documento do fornecedor), como o TSE publica. | publico-agente-publico |  |
| `fotos_ac` | Arquivos de foto do pacote do TSE para AC (nome e tamanho de cada imagem; o pacote original está no landing). | publico-agente-publico |  |
| `fotos_al` | Arquivos de foto do pacote do TSE para AL (nome e tamanho de cada imagem; o pacote original está no landing). | publico-agente-publico |  |
| `fotos_am` | Arquivos de foto do pacote do TSE para AM (nome e tamanho de cada imagem; o pacote original está no landing). | publico-agente-publico |  |
| `fotos_ap` | Arquivos de foto do pacote do TSE para AP (nome e tamanho de cada imagem; o pacote original está no landing). | publico-agente-publico |  |
| `fotos_ba` | Arquivos de foto do pacote do TSE para BA (nome e tamanho de cada imagem; o pacote original está no landing). | publico-agente-publico |  |
| `fotos_br` | Arquivos de foto do pacote do TSE para BR (nome e tamanho de cada imagem; o pacote original está no landing). | publico-agente-publico |  |
| `fotos_ce` | Arquivos de foto do pacote do TSE para CE (nome e tamanho de cada imagem; o pacote original está no landing). | publico-agente-publico |  |
| `fotos_df` | Arquivos de foto do pacote do TSE para DF (nome e tamanho de cada imagem; o pacote original está no landing). | publico-agente-publico |  |
| `fotos_es` | Arquivos de foto do pacote do TSE para ES (nome e tamanho de cada imagem; o pacote original está no landing). | publico-agente-publico |  |
| `fotos_go` | Arquivos de foto do pacote do TSE para GO (nome e tamanho de cada imagem; o pacote original está no landing). | publico-agente-publico |  |
| `fotos_ma` | Arquivos de foto do pacote do TSE para MA (nome e tamanho de cada imagem; o pacote original está no landing). | publico-agente-publico |  |
| `fotos_mg` | Arquivos de foto do pacote do TSE para MG (nome e tamanho de cada imagem; o pacote original está no landing). | publico-agente-publico |  |
| `fotos_ms` | Arquivos de foto do pacote do TSE para MS (nome e tamanho de cada imagem; o pacote original está no landing). | publico-agente-publico |  |
| `fotos_mt` | Arquivos de foto do pacote do TSE para MT (nome e tamanho de cada imagem; o pacote original está no landing). | publico-agente-publico |  |
| `fotos_pa` | Arquivos de foto do pacote do TSE para PA (nome e tamanho de cada imagem; o pacote original está no landing). | publico-agente-publico |  |
| `fotos_pb` | Arquivos de foto do pacote do TSE para PB (nome e tamanho de cada imagem; o pacote original está no landing). | publico-agente-publico |  |
| `fotos_pe` | Arquivos de foto do pacote do TSE para PE (nome e tamanho de cada imagem; o pacote original está no landing). | publico-agente-publico |  |
| `fotos_pi` | Arquivos de foto do pacote do TSE para PI (nome e tamanho de cada imagem; o pacote original está no landing). | publico-agente-publico |  |
| `fotos_pr` | Arquivos de foto do pacote do TSE para PR (nome e tamanho de cada imagem; o pacote original está no landing). | publico-agente-publico |  |
| `fotos_rj` | Arquivos de foto do pacote do TSE para RJ (nome e tamanho de cada imagem; o pacote original está no landing). | publico-agente-publico |  |
| `fotos_rn` | Arquivos de foto do pacote do TSE para RN (nome e tamanho de cada imagem; o pacote original está no landing). | publico-agente-publico |  |
| `fotos_ro` | Arquivos de foto do pacote do TSE para RO (nome e tamanho de cada imagem; o pacote original está no landing). | publico-agente-publico |  |
| `fotos_rr` | Arquivos de foto do pacote do TSE para RR (nome e tamanho de cada imagem; o pacote original está no landing). | publico-agente-publico |  |
| `fotos_rs` | Arquivos de foto do pacote do TSE para RS (nome e tamanho de cada imagem; o pacote original está no landing). | publico-agente-publico |  |
| `fotos_sc` | Arquivos de foto do pacote do TSE para SC (nome e tamanho de cada imagem; o pacote original está no landing). | publico-agente-publico |  |
| `fotos_se` | Arquivos de foto do pacote do TSE para SE (nome e tamanho de cada imagem; o pacote original está no landing). | publico-agente-publico |  |
| `fotos_sp` | Arquivos de foto do pacote do TSE para SP (nome e tamanho de cada imagem; o pacote original está no landing). | publico-agente-publico |  |
| `fotos_to` | Arquivos de foto do pacote do TSE para TO (nome e tamanho de cada imagem; o pacote original está no landing). | publico-agente-publico |  |
| `receitas_candidatos` | Receitas declaradas na prestação de contas dos candidatos de todos os cargos, uma linha por receita, só com as colunas do total (sem nome nem documento de quem doou), como o TSE publica. | publico-agente-publico |  |
| `vagas` | Quantidade de vagas de cada cargo em cada unidade eleitoral nas eleições gerais (por exemplo, 513 de deputado federal), uma linha por cargo e unidade, como o TSE publica. | publico-agente-publico |  |
| `votacao` | Votos de cada candidato (todos os cargos) por município e zona nas eleições gerais já carregadas, como o TSE publica. | publico-agente-publico |  |

## staging

| Tabela | O que é | Sensibilidade | Grain |
| --- | --- | --- | --- |
| `stg_camara__deputados` | Deputados, uma linha por deputado, com nomes padronizados e tipos corretos. | publico-agente-publico |  |
| `stg_camara__deputados_detalhe` | Cadastro dos deputados (só dos já buscados), uma linha por deputado. | publico-agente-publico |  |
| `stg_camara__deputados_historico` | Histórico de situação dos deputados (só dos já buscados), uma linha por registro de status. | publico-agente-publico |  |
| `stg_camara__deputados_ocupacoes` | Ocupações anteriores declaradas por deputado. | publico-agente-publico |  |
| `stg_camara__deputados_profissoes` | Profissões declaradas por deputado. Deputado sem profissão declarada vem da fonte com título vazio e fica aqui com `titulo` nulo (lacuna medida, não preenchida); quem consome filtra. | publico-agente-publico |  |
| `stg_camara__frentes` | Frentes parlamentares, uma por frente. | publico-agente-publico |  |
| `stg_camara__frentes_membros` | Participação de deputados em frentes parlamentares, uma linha por legislatura e título. Em parte das linhas (coordenações antigas) a fonte não identifica o deputado; elas ficam aqui e saem dos marts. | publico-agente-publico |  |
| `stg_camara__legislaturas` | Legislaturas, uma linha por legislatura, com datas oficiais. | publico-agente-publico |  |
| `stg_camara__orgaos` | Órgãos da Câmara, um por órgão, com a URL da fonte. | publico-agente-publico |  |
| `stg_camara__orgaos_membros` | Participação de deputados em órgãos, uma linha por cargo e período. | publico-agente-publico |  |
| `stg_camara__partidos` | Partidos, uma linha por partido. | publico-agente-publico |  |
| `stg_camara__proposicoes` | Proposições com a última situação. A ementa fica como veio da fonte. | publico-agente-publico |  |
| `stg_camara__proposicoes_autores` | Autores de proposições (deputados, comissões, Senado, Executivo...), por ordem de assinatura. | publico-agente-publico |  |
| `stg_camara__tramitacoes` | Tramitação das proposições que podem virar norma (só as já buscadas), uma linha por andamento. | publico-agente-publico |  |
| `stg_camara__votacoes` | Votações com resultado e totais oficiais. | publico-agente-publico |  |
| `stg_camara__votacoes_objetos` | Proposições que são objeto de votação. | publico-agente-publico |  |
| `stg_camara__votacoes_orientacoes` | Orientação de cada bancada em cada votação. | publico-agente-publico |  |
| `stg_camara__votacoes_proposicoes` | Proposições afetadas por votação. | publico-agente-publico |  |
| `stg_camara__votos` | Voto de cada deputado em cada votação nominal. Voto vazio fica como texto vazio. | publico-agente-publico |  |
| `stg_constituicao__linhas` | Uma linha por parágrafo de texto do arquivo da Constituição e do ADCT, como publicado. | publico-agente-publico |  |
| `stg_ibge__municipios` | Municípios do IBGE, uma linha por município. | publico-agente-publico |  |
| `stg_identity__pessoas` | Pessoas do projeto (chave própria). | publico-agente-publico |  |
| `stg_identity__pessoas_fusoes` | Chaves de pessoa absorvidas por outra quando se mostraram a mesma pessoa, uma linha por chave absorvida. | publico-agente-publico |  |
| `stg_identity__pessoas_identificadores` | Identificadores de cada pessoa em cada fonte. | publico-agente-publico |  |
| `stg_metadata__capturas` | Capturas dos arquivos da fonte (um arquivo, uma linha). `id_captura` liga as linhas do raw ao arquivo. | publico-agente-publico |  |
| `stg_senado__exercicios` | Exercício oficial de cada senador em cada mandato (titular ou suplente), com a causa de afastamento. | publico-agente-publico |  |
| `stg_senado__normas` | Catálogo das normas federais, uma linha por norma, só metadados, com a ementa padronizada e a original. | publico-agente-publico |  |
| `stg_senado__normas_publicacoes` | Publicações de cada norma detalhada (e da Constituição) no Diário Oficial, uma linha por norma e publicação. | publico-agente-publico |  |
| `stg_senado__normas_relacoes` | Relações de cada norma detalhada (e da Constituição) com atos posteriores, uma linha por norma, ato e tipo de relação. | publico-agente-publico |  |
| `stg_senado__processos` | Processo de cada matéria votada (só as já buscadas), com a situação atual e a norma gerada. | publico-agente-publico |  |
| `stg_senado__senadores` | Senadores, uma linha por senador (o mais recente dos arquivos de legislatura), com nomes padronizados. | publico-agente-publico |  |
| `stg_senado__senadores_detalhe` | Detalhe de cada senador (só os já buscados), com nome civil, nascimento, naturalidade e foto. | publico-agente-publico |  |
| `stg_senado__vetos` | Vetos presidenciais apreciados pelo Congresso, uma linha por veto, com a matéria vetada e a norma gerada. | publico-agente-publico |  |
| `stg_senado__vetos_dispositivos` | Dispositivos vetados de cada veto buscado, com o texto vetado, a razão do veto e a situação. | publico-agente-publico |  |
| `stg_senado__vetos_votos` | Voto nominal de cada deputado e senador num dispositivo vetado, sem o código do parlamentar. | publico-agente-publico |  |
| `stg_senado__votacoes` | Votações em plenário com resultado, totais e a matéria votada. Votação secreta tem `secreta` verdadeiro. | publico-agente-publico |  |
| `stg_senado__votos` | Voto de cada senador em cada votação nominal. Em votação secreta a sigla é "Votou". | publico-agente-publico |  |
| `stg_transparencia__compras` | Contratos do governo federal, um por linha, de 2022-11 em diante. Contratado pessoa física vem com CPF completo na fonte e sai mascarado aqui. | publico-dados-pessoais-de-terceiros | numero_contrato + cd_ug |
| `stg_transparencia__compras_itens` | Itens dos contratos do governo federal. | publico-dados-pessoais-de-terceiros | numero_contrato + cd_ug + cd_item |
| `stg_transparencia__compras_termos_aditivos` | Termos aditivos dos contratos do governo federal. | publico-dados-pessoais-de-terceiros | numero_contrato + cd_ug + numero_termo_aditivo |
| `stg_transparencia__despesas` | Execução da despesa federal por mês, órgão, unidade gestora, ação e natureza da despesa, com os valores empenhado, liquidado e pago. Não traz favorecido (o arquivo não o publica). | publico-agente-publico | mês, órgão subordinado, unidade gestora, gestão, unidade orçamentária, plano orçamentário, subtítulo, localizador, autor da emenda, elemento e modalidade da despesa |
| `stg_transparencia__emendas` | Emendas parlamentares, uma linha por emenda, localidade, função, programa e ação. | publico-agente-publico |  |
| `stg_transparencia__emendas_convenios` | Convênios firmados com recursos de emendas parlamentares. | publico-agente-publico |  |
| `stg_transparencia__emendas_favorecidos` | Quem recebeu o dinheiro de cada emenda, por mês, como a fonte publica (inclui pessoa física, com CPF mascarado). | publico-agente-publico |  |
| `stg_transparencia__licitacoes` | Licitações do governo federal (SIASG), uma por linha, de 2022-11 em diante, só meses fechados. | publico-agente-publico | unidade gestora, modalidade e número da licitação |
| `stg_transparencia__licitacoes_empenhos` | Empenhos relacionados às licitações do governo federal. | publico-agente-publico | licitação e empenho |
| `stg_transparencia__licitacoes_itens` | Itens das licitações do governo federal, com o vencedor. Vencedor pessoa física vem com CPF completo na fonte e sai mascarado aqui. | publico-dados-pessoais-de-terceiros | linha da fonte: item e vencedor (a fonte repete linhas idênticas e deixa o código do item vazio em parte delas) |
| `stg_transparencia__licitacoes_participantes` | Participantes dos itens das licitações do governo federal, com a marca de vencedor. Participante pessoa física vem com CPF completo na fonte e sai mascarado aqui. | publico-dados-pessoais-de-terceiros | linha da fonte: item e participante (a fonte repete linhas idênticas) |
| `stg_tse__bens` | Bens declarados pelos candidatos de todos os cargos, uma linha por bem. | publico-agente-publico |  |
| `stg_tse__candidaturas` | Candidaturas de todos os cargos nas eleições gerais e municipais, uma linha por candidatura e turno. | publico-agente-publico |  |
| `stg_tse__despesas_candidatos` | Despesas contratadas declaradas pelos candidatos de todos os cargos, uma linha por despesa; o valor é o declarado, sem nome nem documento do fornecedor. | publico-agente-publico |  |
| `stg_tse__fotos` | Arquivos de foto oficial das candidaturas das eleições gerais, um por imagem dentro de cada pacote por UF do TSE. | publico-agente-publico |  |
| `stg_tse__receitas_candidatos` | Receitas declaradas pelos candidatos de todos os cargos, uma linha por receita; o valor é o declarado, sem nome nem documento de quem doou. | publico-agente-publico |  |
| `stg_tse__vagas` | Vagas de cada cargo em cada unidade eleitoral, uma linha por eleição, cargo e unidade, como o TSE publica; traz também as eleições suplementares. | publico-agente-publico |  |
| `stg_tse__votacao` | Votos de cada candidato (todos os cargos) por município e zona, como o TSE publica. | publico-agente-publico |  |

## intermediate

| Tabela | O que é | Sensibilidade | Grain |
| --- | --- | --- | --- |
| `int_deputados_frentes_fotos` | Uma foto por deputado, a da legislatura mais recente nos arquivos de frentes. | publico-agente-publico |  |
| `int_deputados_ids_unidos` | Todo deputado informado pela Câmara (cadastro mais votos). | publico-agente-publico |  |
| `int_deputados_votos_agregados` | Um registro por deputado visto nos votos, com nome e foto mais recentes. | publico-agente-publico |  |
| `int_ementas_siglas_extraidas` | Siglas escritas em maiúsculas dentro de ementas de caixa mista. | publico-agente-publico |  |
| `int_frentes_membros_ligados` | Participação em frentes ligada à pessoa do projeto. | publico-agente-publico |  |
| `int_orgaos_membros_ligados` | Participação em órgãos ligada à pessoa do projeto. | publico-agente-publico |  |
| `int_pessoas_ids_vistos` | Todo identificador de pessoa informado pelas fontes. Entrada do código de identidade. | publico-agente-publico |  |
| `int_pessoas_profissoes_agregadas` | Uma linha por pessoa, com as profissões declaradas. | publico-agente-publico |  |
| `int_pessoas_senado_unidas` | Pessoa do projeto unida ao cadastro do Senado. | publico-agente-publico |  |
| `int_pessoas_unidas_cadastro` | Pessoa do projeto unida ao cadastro e aos dados vistos nos votos. | publico-agente-publico |  |
| `int_pessoas_vinculo` | Pessoas das duas casas com nome civil (como chave) e nascimento, para ligar entre fontes. | publico-agente-publico |  |
| `int_proposicoes_autorias_ligadas` | Autorias com a pessoa do projeto; autor que não é deputado fica sem pessoa. | publico-agente-publico |  |
| `int_senado_materias_unicas` | Uma linha por matéria votada no Senado, com os dados da votação mais recente. | publico-agente-publico |  |
| `int_senadores_unidos` | Todo senador informado pelo Senado (cadastro mais votos). | publico-agente-publico |  |
| `int_tse_eleitos` | Quem foi eleito, com a base: informado (o TSE diz Eleito) ou derivado (disputa de uma vaga de eleição passada em que o TSE não informa o vencedor; vale o mais votado do último turno, art. 77, 28 e 29 da Constituição). Entrada da identidade e dos mandatos. | publico-agente-publico |  |
| `int_tse_eleitos_grupos` | As candidaturas do TSE de quem foi eleito pelo menos uma vez, agrupadas por pessoa entre as eleições. Entrada da identidade (ADR 0031): é daqui que nascem as pessoas de todo eleito. O grupo não é estável; a identidade usa a candidatura, que é. | publico-agente-publico |  |
| `int_tse_pessoas` | Identificador da mesma pessoa entre as eleições do TSE, por nome civil ou nome de urna com a mesma data de nascimento (cada chave única em cada eleição e sem datas de 1º de janeiro); a ligação se propaga entre candidaturas que partilham uma chave. Uma linha por candidatura ligável. | publico-agente-publico |  |
| `int_vinculos_propostos` | Vínculos propostos entre fontes pela regra de nome civil e nascimento iguais e únicos: Câmara com Senado (mesma pessoa) e candidatura do TSE com a pessoa. Entrada da identidade. | publico-agente-publico |  |
| `int_votacoes_proposicoes_unidas` | Proposições de cada votação, com o papel (afetada ou objeto). | publico-agente-publico |  |
| `int_votacoes_votos_ligados` | Votos com a pessoa do projeto (chave própria). | publico-agente-publico |  |

## marts

| Tabela | O que é | Sensibilidade | Grain |
| --- | --- | --- | --- |
| `agg_composicoes` | Quem ocupa cada cargo em cada corte (1º de janeiro e 1º de julho, de 1997 até hoje, e a posse de cada legislatura), por território e partido. A composição eleita (quem foi eleito para o mandato que cobre o corte; o fim é derivado da duração do cargo) e a composição em exercício (quem de fato exercia o cargo, só deputado federal e senador, com o partido mais recente conhecido até o corte) são sempre separadas, porque respondem coisas diferentes. Mandato sem início não aparece na eleita. O prefixo analise_ do modelo é só pela colisão de nomes; a tabela é agg_composicoes. | publico | corte |
| `agg_pessoas_atividade` | O que cada parlamentar fez, derivado dos votos e das autorias: quantidade de votos e de propostas, legislaturas com voto e o partido e a UF do voto mais recente. Fica fora do cadastro (dim_pessoas_cadastro) porque muda a cada carga, enquanto o cadastro só descreve a pessoa. Uma linha por pessoa do cadastro (Câmara e Senado); quem não votou tem zero votos e o resto vazio. O partido e a UF são os do voto, como a fonte informa, e não afirmam filiação. | publico-agente-publico | pessoa |
| `brg_frentes_membros` | Participação de pessoas em frentes parlamentares, com o título e a legislatura. Uma linha por pessoa, frente, legislatura e título. | publico-agente-publico | pessoa |
| `brg_licitacoes_empenhos` | Ponte entre as licitações do governo federal e os empenhos relacionados a elas, como o Portal da Transparência publica. Uma linha por licitação e empenho. | publico-agente-publico | licitação e empenho |
| `brg_normas_relacoes` | Ligações de cada norma com atos posteriores, como o Senado declara (alteração, regulamentação, veto, declaração de constitucionalidade). Só das normas detalhadas (leis, leis complementares, emendas, medidas provisórias e a Constituição). Uma linha por norma, ato posterior e tipo de relação. | publico | norma |
| `brg_orgaos_membros` | Participação de pessoas em órgãos da Câmara, com cargo e período. Uma linha por pessoa, órgão, cargo e período informado. | publico-agente-publico | pessoa |
| `brg_pessoas_ocupacoes` | Ocupações anteriores declaradas. Uma linha por pessoa e ocupação. | publico-agente-publico | pessoa e ocupação |
| `brg_proposicoes_autorias` | Autores de cada proposição (deputados e também comissão, Senado, Executivo e outros), com a posição na assinatura e o total de autores; id_pessoa só existe quando o autor é deputado. Uma linha por autor e proposição. | publico-agente-publico | autor e proposição |
| `brg_votacoes_proposicoes` | Que proposição (ou matéria) cada votação decidiu, uma linha por votação e proposição, com o papel. Troca a lista em texto de fct_votacoes por linhas que ligam a fct_proposicoes. Câmara: afetada (a votação mudou a situação da proposição) ou objeto (foi o assunto votado). Senado: a matéria da votação. Votação sem proposição na fonte não tem linha. O prefixo fatos_ do modelo é só pela colisão de nomes; a tabela é brg_votacoes_proposicoes. | publico | votação e proposição |
| `dim_constituicao_dispositivos` | A Constituição de 1988 e o ADCT dispositivo a dispositivo, como a Câmara publica (texto atualizado até a emenda indicada). O tipo e o contexto saem da posição e do começo de cada linha; o texto não é reescrito. Uma linha por parágrafo do arquivo. | publico | parágrafo do arquivo |
| `dim_disputas` | Cada cargo em cada unidade eleitoral de uma eleição, com o número de vagas que o TSE informa. Uma linha por eleição, cargo e unidade. É a base das candidaturas e dos resultados, e permite medir se alguma vaga ficou sem eleito. | publico | eleição |
| `dim_eleicoes` | Eleições do arquivo de vagas do TSE, uma por ano e código do TSE, ordinárias e suplementares. Se a eleição é ordinária é regra do projeto (cobertura de unidades por ano e cargo), e não informação do TSE. | publico | eleição |
| `dim_frentes` | Frentes parlamentares, com legislatura de criação e coordenador. Uma linha por frente. | publico | frente parlamentar |
| `dim_legislaturas` | Legislaturas da Câmara, com datas oficiais de início e fim. Uma linha por legislatura. | publico | legislatura |
| `dim_municipios` | Municípios do Brasil segundo o IBGE, com UF e região. Uma linha por município. | publico | município |
| `dim_municipios_codigos_tse` | De-para entre o código de município do TSE e o do IBGE, por nome e UF únicos dos dois lados. Uma linha por município do TSE; sem correspondência fica com o código do IBGE vazio. | publico | município do TSE |
| `dim_orgaos` | Os órgãos onde o mandato é exercido: comissões, plenário, mesa diretora e conselhos da Câmara. A chave id_orgao é do projeto (fonte e identificador da fonte); o identificador da fonte fica ao lado para auditoria. Senado, assembleias e câmaras municipais ainda não têm fonte carregada. | publico | órgão |
| `dim_partidos_camara` | Partidos com sigla e nome oficiais. Uma linha por partido. | publico | partido |
| `dim_partidos_linhagem` | Mudanças de nome, fusões e incorporações de partidos, conforme o TSE, com a página oficial de cada evento. Curada à mão; só o que foi conferido. Uma linha por partido de origem e evento. | publico | partido de origem e evento |
| `dim_pessoas` | Quem já teve pelo menos um cargo (ADR 0030 e 0031): parlamentar da Câmara ou do Senado e todo eleito do TSE, a partir do momento da eleição. Quem só se candidatou e nunca foi eleito não está aqui. Uma linha por pessoa do projeto, com a chave de identidade que nunca muda nem é reaproveitada. Cada atributo diz de qual fonte veio (a Câmara e o Senado valem mais que o TSE; o TSE vale a candidatura mais recente que o traz). Só o que a fonte publica; nada é inferido. | publico-agente-publico | pessoa |
| `dim_pessoas_cadastro` | Cadastro parlamentar: só Câmara e Senado (cerca de 8,5 mil pessoas), com o que só as casas publicam: contato institucional, gabinete, redes, situação e falecimento. A atividade legislativa (contagens e último partido) está em agg_pessoas_atividade. Uma linha por pessoa. A ficha completa da pessoa, inclusive o que vem do TSE com `fonte_*` por atributo, está em dim_pessoas (cerca de 322 mil pessoas). | publico-agente-publico | pessoa |
| `dim_territorios` | Territórios do país em uma só tabela: o Brasil, as 27 UFs e os municípios, cada um com a chave do IBGE e, nos municípios, o código do TSE quando a ligação por nome e UF é única. Uma linha por território. Chave de todo fato que fala de lugar (ADR 0030). | publico | território |
| `fct_campanhas` | A campanha de cada candidatura, só com arquivos do TSE: bens declarados, receitas e despesas da prestação de contas. Uma linha por candidatura que tenha ao menos um desses dados. O total fica vazio, e não zero, quando o arquivo daquele dado não foi carregado ou não traz o candidato. | publico-agente-publico | candidatura |
| `fct_candidaturas` | Cada candidatura de uma eleição ordinária, como o TSE registrou, de todos os cargos (inclusive vereador): quem era, por qual partido, em qual disputa, o desfecho e a foto oficial. Só arquivos do TSE, sem Câmara, Senado nem pessoa do projeto. Uma linha por candidatura; os turnos estão em resultados e a campanha em campanhas. A mesma pessoa em eleições diferentes é achada por id_pessoa_tse; sem ele a candidatura não tem histórico, o que não quer dizer novato. fl_eleito vale para o eleito informado pelo TSE ou derivado dos votos pela Constituição (base_eleicao diz qual; o texto original do TSE segue em resultado); fl_eleito_informado guarda só o informado. | publico-agente-publico | candidatura |
| `fct_candidaturas_bens` | Bens declarados à Justiça Eleitoral por candidatos que já são pessoa do projeto, de 2006 em diante, como o TSE publica (valor declarado, sem correção). Uma linha por bem. | publico-agente-publico | candidatura e bem |
| `fct_candidaturas_votos` | Votos de cada candidatura de quem já é pessoa do projeto, somados dos municípios e zonas, nas eleições gerais já carregadas. Uma linha por candidatura e turno. | publico-agente-publico | candidatura e turno |
| `fct_cargos_ocupacoes` | Cada período em que uma pessoa ocupa um cargo num território: a camada semântica da ocupação, que junta o exercício publicado pela Câmara e pelo Senado (fim real, suplente que assumiu, eleito em eleição suplementar) e o mandato da eleição (fct_mandatos), que cobre quem foi eleito e ainda não assumiu e os cargos sem fonte de exercício (vereador, prefeito, governador, presidente, deputado estadual), com o fim previsto pela duração do cargo. O exercício vence: o mandato que ele cumpre não gera outra linha. Cassação e renúncia dos cargos sem exercício não aparecem (issue 162). Quem filtra a data usa dt_inicio e dt_fim. | publico-agente-publico | período de ocupação |
| `fct_constituicao_alteracoes` | Cada indicação de emenda que o texto da Constituição traz entre parênteses, por dispositivo (por exemplo, Redação dada pela Emenda Constitucional nº 45, de 2004). Uma linha por dispositivo e emenda citada. | publico | dispositivo e emenda citada |
| `fct_emendas` | Emendas parlamentares ao orçamento federal como o Portal da Transparência publica, com valores empenhado, liquidado e pago. O autor vem pelo nome e pelo código do SIAFI (não é o código do parlamentar); a pessoa é derivada só para emenda individual, quando o nome é o de uma só pessoa com mandato federal no ano da emenda ou no anterior (ADR 0056), e fica vazia no resto. Uma linha por emenda, localidade, função, programa e ação. | publico | emenda |
| `fct_emendas_convenios` | Convênios firmados com recursos de emendas parlamentares, como o Portal da Transparência publica, com convenente, objeto e valor. Uma linha por convênio e emenda. | publico | convênio e emenda |
| `fct_emendas_favorecidos` | Quem recebeu o dinheiro de cada emenda parlamentar, por mês, como o Portal da Transparência publica. Inclui pessoa física (cidadão comum, com CPF mascarado); contem_dado_pessoal marca essas linhas. Uma linha por emenda, favorecido e mês. | publico-dados-pessoais-de-terceiros | emenda |
| `fct_eventos` | A linha do tempo da pessoa, uma linha por evento, DERIVADA dos fatos tipados (a verdade está neles; aqui não há texto livre). O tipo vem do catálogo fechado dim_evento_tipos e fato_origem diz de qual fato a linha nasceu. ano_evento sempre existe; dt_evento só quando a fonte dá o dia (eleição e candidatura só têm o ano). Tipos sem fato carregado (diplomação, nomeação, exoneração, entrada e saída de órgão, filiação e desfiliação por data, retorno de afastamento) ainda não têm linha: o teste eventos_de_tipo_sem_fato lista quais. O prefixo fatos_ do modelo é só pela colisão de nomes; a tabela é fct_eventos. | publico-agente-publico | evento da pessoa |
| `fct_exercicios` | Cada período em que alguém exerceu de fato um mandato federal, como a fonte oficial publica: deputados federais (Câmara, a partir do histórico de entradas e saídas) e senadores, titulares e suplentes (Senado). Os campos da fonte não são derivados; as colunas que ligam o período ao resto (id_candidatura, id_partido) são derivadas e marcadas (base_partido). Quem foi eleito e nunca assumiu não tem linha; vereador, prefeito, governador e presidente não entram, pois não há fonte oficial de exercício carregada para eles (o mandato deles está em fct_mandatos; a ocupação dos dois juntos, em fct_cargos_ocupacoes). O nome do modelo leva o prefixo fatos_ só porque pode haver colisão futura com marts; a tabela é fct_exercicios. | publico-agente-publico | período de exercício |
| `fct_licitacoes` | Licitações do governo federal (SIASG), de 2022-11 em diante (só meses fechados), como o Portal da Transparência publica. Uma linha por unidade gestora, modalidade e número da licitação; se a fonte repete a licitação em mais de um mês, vale a captura mais recente. | publico-agente-publico | licitação (unidade gestora |
| `fct_licitacoes_itens` | Itens das licitações do governo federal, com o vencedor, uma linha por item e vencedor como a fonte publica (a fonte repete linhas idênticas e deixa o código do item vazio em parte delas; o teste de lacunas as mede). Vencedor pessoa física tem o CPF mascarado; `fl_contem_dado_pessoal` marca essas linhas. | publico-dados-pessoais-de-terceiros | item e vencedor |
| `fct_licitacoes_participantes` | Participantes dos itens das licitações do governo federal, com a marca de vencedor, uma linha por item e participante como a fonte publica (a fonte repete linhas idênticas). Participante pessoa física tem o CPF mascarado; `fl_contem_dado_pessoal` marca essas linhas. | publico-dados-pessoais-de-terceiros | item e participante |
| `fct_mandatos` | Um mandato por candidatura eleita, de todos os cargos (inclusive vereador e o vice e os suplentes eleitos junto): o mandato nasce da eleição, não do exercício. Quem assumiu depois como suplente não tem linha aqui (será fct_exercicios). O início vem da regra da Constituição com a vigência (dim_cargos_posse) ou, para deputado estadual e distrital, da posse que a constituição estadual fixa por UF (dim_cargos_posse_uf, só UFs com fonte conferida); onde nenhuma fixa a data, da data de posse do TSE quando plausível. O fim é sempre derivado da duração do cargo. Só TSE; a ligação com a pessoa do projeto virá com as pessoas de todos os eleitos. O nome do modelo leva o prefixo fatos_ só porque fct_mandatos ainda existe; a tabela é fct_mandatos. | publico-agente-publico | mandato (candidatura eleita) |
| `fct_normas` | Catálogo das normas federais (leis, decretos, medidas provisórias, emendas...) desde 1808, só metadados; o texto integral não vem desta fonte. Uma linha por norma. | publico | norma |
| `fct_normas_geradas` | Norma jurídica que resultou de uma matéria, com número, datas e veículo de publicação. Só o Senado informa por enquanto. Uma linha por matéria. | publico | matéria |
| `fct_normas_publicacoes` | Onde cada norma foi publicada no Diário Oficial (a original e, por exemplo, a do veto), com página e coluna. Só das normas detalhadas. Uma linha por norma e publicação. | publico | norma e publicação |
| `fct_pessoas_fusoes` | Chaves de pessoa absorvidas por outra quando se mostraram a mesma pessoa (por exemplo, deputado que virou senador). Uma linha por chave absorvida. | publico-agente-publico | chave absorvida |
| `fct_pessoas_partidos` | O partido de cada pessoa em cada momento, de fontes oficiais (ADR 0032): o histórico de deputados da Câmara (períodos em que o deputado aparece em um partido), os votos de deputados e senadores (o partido em cada voto, só para quem não tem histórico) e a candidatura do TSE (o partido pelo qual a pessoa concorreu em cada eleição, para toda pessoa que já foi eleita, inclusive vereador, prefeito e governador que nunca estiveram na Câmara). Troca de partido são dois momentos seguidos da mesma pessoa com partidos diferentes. O partido da candidatura não é a data de filiação, e a filiação partidária por data (arquivo de filiados do TSE) não é carregada: ver a base legal em docs/03-consultar/05-lgpd-dados-pessoais.md. O prefixo fatos_ do modelo é só pela colisão de nomes; a tabela é fct_pessoas_partidos. | publico-agente-publico | partido de uma pessoa em um momento por fonte |
| `fct_proposicoes` | Proposições com ementa padronizada, ementa oficial, situação atual e URL da fonte. Uma linha por proposição. | publico | proposição |
| `fct_proposicoes_tramitacoes` | Andamentos das proposições que podem virar norma (só as já buscadas), na ordem em que ocorreram. Uma linha por proposição, sequência e hora (a fonte às vezes repete a sequência com outra hora). | publico | proposição, sequência e hora |
| `fct_resultados` | O que aconteceu em cada turno da eleição, candidatura a candidatura, só com arquivos do TSE. Uma linha por candidatura e turno, de todos os cargos (inclusive vereador). resultado e resultado_votacao são o que cada arquivo do TSE informa e podem estar vazios (em 2006 o TSE não informa quem venceu o 2º turno de presidente). fl_mais_votado_no_turno é derivado dos votos e não é resultado do TSE. | publico-agente-publico | candidatura e turno |
| `fct_vetos` | Vetos presidenciais apreciados pelo Congresso, de 1994 em diante (antes disso a fonte não informa), com a matéria vetada, a norma gerada e as datas. Uma linha por veto. | publico | veto |
| `fct_vetos_dispositivos` | Cada dispositivo vetado, com o texto vetado, a razão do veto escrita pela Presidência e o que o Congresso decidiu (situação como a fonte informa). Só dos vetos já buscados. Uma linha por dispositivo. | publico | dispositivo vetado |
| `fct_vetos_votos` | Voto de deputados e senadores em cada dispositivo vetado votado, como a fonte entrega (nome, partido e UF, sem o código do parlamentar), por isso não ligado a pessoas. Só dos dispositivos já buscados. Uma linha por dispositivo e voto. | publico-agente-publico | dispositivo e voto |
| `fct_votacoes` | Votações com resultado oficial, totais e proposições. Uma linha por votação. | publico | votação |
| `fct_votos` | O voto nominal de cada parlamentar em cada votação (Câmara e Senado), com o partido que a pessoa tinha na data do voto como chave (id_partido) e a sigla da fonte ao lado. A sigla pode ser de dois partidos (duas legendas diferentes em épocas diferentes): vale o partido cujo período de uso da sigla está mais perto do ano do voto. Sem partido ("S.Part.", "Sem registro") ou com sigla ainda não curada, o id_partido fica vazio; o teste de aviso mede as não curadas. Só votos de quem tem pessoa no projeto. | publico-agente-publico | voto de um parlamentar em uma votação |

## identity

| Tabela | O que é | Sensibilidade | Grain |
| --- | --- | --- | --- |
| `pessoas` | Pessoa do projeto, com chave própria, independente da fonte. | publico-agente-publico |  |
| `pessoas_fusoes` | Chaves de pessoa absorvidas por outra quando se mostraram a mesma pessoa. | publico-agente-publico |  |
| `pessoas_identificadores` | Ponte entre a chave da pessoa e o identificador em cada fonte, com método e confirmação. | publico-agente-publico |  |

## metadata

| Tabela | O que é | Sensibilidade | Grain |
| --- | --- | --- | --- |
| `capturas` | Cada arquivo recebido da fonte, com URL, hash, caminho no landing e datas. | controle |  |
| `execucoes` | Cada execução de etapa do pipeline, com início, fim, versão do código e resultado. | controle |  |
| `fontes_verificacoes` | Verificações de cada fonte (disponibilidade, carga, volume), com resultado e detalhe; cada linha é um instante, vale a mais recente de cada tipo. | controle |  |
| `testes_resultados` | Resultado de cada modelo e teste do dbt na última execução de cada comando. | controle |  |

## Dicionário de colunas dos marts

### marts.agg_composicoes

| Coluna | Tipo | Descrição | Dado pessoal |
| --- | --- | --- | --- |
| `dt_corte` | date | Data do corte: 1º de janeiro, 1º de julho ou a posse de uma legislatura (dim_legislaturas). |  |
| `tipo_composicao` | varchar | eleita (quem foi eleito para o mandato que cobre o corte) ou exercicio (quem de fato exercia o cargo). |  |
| `id_cargo` | varchar | Cargo (dim_cargos). |  |
| `id_territorio` | varchar | Território da composição (dim_territorios): município, UF ou país; vazio onde a fonte não liga a um território. |  |
| `id_partido` | integer | Partido (dim_partidos): o da eleição na composição eleita, o mais recente conhecido até o corte na composição em exercício; vazio quando não se conhece. |  |
| `qtd_membros` | bigint | Quantas pessoas ocupam o cargo naquele corte, território e partido. |  |

### marts.agg_pessoas_atividade

| Coluna | Tipo | Descrição | Dado pessoal |
| --- | --- | --- | --- |
| `id_pessoa` | bigint | Pessoa (dim_pessoas_cadastro). |  |
| `qtd_votos` | bigint | Quantidade de votos nominais registrados. |  |
| `qtd_propostas` | bigint | Quantidade de proposições em que consta como autora ou apoiadora; vazio onde a fonte não informa autoria (Senado). |  |
| `ultimo_partido` | varchar | Sigla do partido no voto mais recente, como a fonte informa. |  |
| `ultima_uf` | varchar | UF no voto mais recente. |  |
| `dt_ultimo_voto` | timestamp | Data e hora do voto mais recente. |  |
| `primeira_legislatura_com_voto` | integer | Primeira legislatura em que há voto registrado. |  |
| `ultima_legislatura_com_voto` | integer | Última legislatura em que há voto registrado. |  |

### marts.brg_frentes_membros

| Coluna | Tipo | Descrição | Dado pessoal |
| --- | --- | --- | --- |
| `fonte` | varchar | Fonte oficial do registro. |  |
| `id_frente` | bigint | Frente (dim_frentes). |  |
| `id_pessoa` | bigint | Chave da pessoa (dim_pessoas_cadastro). |  |
| `titulo` | varchar | Título na frente (coordenador, membro etc.). |  |
| `id_legislatura` | integer | Legislatura do registro. |  |
| `dt_inicio` | date | Início da participação, quando a fonte informa. |  |
| `dt_fim` | date | Fim da participação, quando a fonte informa. |  |
| `id_captura` | bigint | Captura do arquivo de origem (URL, data e hash em metadata.capturas). |  |
| `dt_captura` | date | Data da captura do arquivo de origem. |  |

### marts.brg_licitacoes_empenhos

| Coluna | Tipo | Descrição | Dado pessoal |
| --- | --- | --- | --- |
| `fonte` | varchar | Fonte oficial do registro. |  |
| `id_licitacao` | varchar | Licitação a que o empenho se relaciona (fct_licitacoes). |  |
| `cd_empenho` | varchar | Código do empenho, como a fonte informa. |  |
| `dt_emissao` | date | Data de emissão do empenho. |  |
| `observacao` | varchar | Observação do empenho, texto livre da fonte (CPF no texto é mascarado pelo projeto). |  |
| `valor` | decimal(18,4) | Valor do empenho, em reais, com as quatro casas que a fonte publica. |  |
| `id_captura` | bigint | Captura do arquivo de origem (URL, data e hash em metadata.capturas). |  |
| `dt_captura` | date | Data da captura do arquivo de origem. |  |

### marts.brg_normas_relacoes

| Coluna | Tipo | Descrição | Dado pessoal |
| --- | --- | --- | --- |
| `fonte` | varchar | Fonte oficial do registro. |  |
| `id_norma` | bigint | Norma de que se fala (fct_normas). |  |
| `tipo_relacao` | varchar | Tipo da relação como a fonte declara (por exemplo, Declaração de Alteração Permanente). |  |
| `id_norma_posterior` | bigint | Ato posterior que se relaciona com a norma. |  |
| `norma_posterior_nome` | varchar | Nome do ato posterior. |  |
| `dt_norma_posterior_assinatura` | date | Data de assinatura do ato posterior. |  |
| `dt_publicacao` | date | Data de publicação do ato posterior. |  |
| `publicacao` | varchar | Publicação do ato posterior no Diário Oficial. |  |
| `dt_captura` | date | Data da captura do arquivo de origem. |  |
| `id_captura` | bigint | Captura do arquivo de origem (URL, data e hash em metadata.capturas). |  |

### marts.brg_orgaos_membros

| Coluna | Tipo | Descrição | Dado pessoal |
| --- | --- | --- | --- |
| `fonte` | varchar | Fonte oficial do registro. |  |
| `id_orgao` | bigint | Órgão (dim_orgaos). Parte dos órgãos citados (Congresso, comissões especiais) não consta da lista de órgãos da fonte; o teste de relação mede essa lacuna. |  |
| `orgao_sigla` | varchar | Sigla do órgão como informada na própria linha de composição. |  |
| `id_pessoa` | bigint | Chave da pessoa (dim_pessoas_cadastro). |  |
| `cargo` | varchar | Cargo no órgão (titular, suplente, presidente etc.). |  |
| `partido` | varchar | Partido informado no registro. |  |
| `uf` | varchar | UF informada no registro. |  |
| `dt_inicio` | date | Início da participação. |  |
| `dt_fim` | date | Fim da participação; vazio se a fonte não informa. |  |
| `id_captura` | bigint | Captura do arquivo de origem (URL, data e hash em metadata.capturas). |  |
| `dt_captura` | date | Data da captura do arquivo de origem. |  |

### marts.brg_pessoas_ocupacoes

| Coluna | Tipo | Descrição | Dado pessoal |
| --- | --- | --- | --- |
| `id_pessoa` | bigint | Chave da pessoa (dim_pessoas_cadastro). |  |
| `titulo` | varchar | Ocupação declarada. |  |
| `entidade` | varchar | Entidade em que exerceu a ocupação. |  |
| `entidade_uf` | varchar | UF da entidade. |  |
| `ano_inicio` | integer | Ano de início; vazio quando a fonte escreve outra coisa que um ano (por exemplo, 1999a2002). |  |
| `ano_inicio_original` | varchar | Ano de início exatamente como a fonte escreve. |  |
| `ano_fim` | integer | Ano de fim; vazio quando a fonte escreve outra coisa que um ano. |  |
| `ano_fim_original` | varchar | Ano de fim exatamente como a fonte escreve. |  |
| `fonte` | varchar | Fonte oficial do registro. |  |
| `id_captura` | bigint | Captura do arquivo de origem (URL, data e hash em metadata.capturas). |  |
| `dt_captura` | date | Data da captura do arquivo de origem. |  |

### marts.brg_proposicoes_autorias

| Coluna | Tipo | Descrição | Dado pessoal |
| --- | --- | --- | --- |
| `id_pessoa` | bigint | Chave da pessoa (dim_pessoas_cadastro); vazia quando o autor não é deputado. |  |
| `fonte` | varchar | Fonte oficial do registro. |  |
| `id_proposicao` | varchar | Identificador da proposição na fonte. |  |
| `ordem_assinatura` | integer | Posição na assinatura. |  |
| `qtd_autores` | bigint | Total de autores da proposição. |  |
| `nome_autor` | varchar | Nome do autor como a fonte informa (deputado, comissão, Senado, Executivo...). |  |
| `tipo_autor` | varchar | Tipo do autor na fonte (deputado, órgão, outro). |  |
| `proponente` | integer | 1 quando consta como proponente; 0 caso contrário. |  |
| `proposicao_fonte_url` | varchar | Endereço da proposição na fonte oficial. |  |
| `id_captura` | bigint | Captura do arquivo de origem (URL, data e hash em metadata.capturas). |  |
| `dt_captura` | date | Data da captura do arquivo de origem. |  |

### marts.brg_votacoes_proposicoes

| Coluna | Tipo | Descrição | Dado pessoal |
| --- | --- | --- | --- |
| `fonte` | varchar | Fonte oficial do registro (camara ou senado). |  |
| `id_votacao` | varchar | Identificador da votação na fonte. |  |
| `id_proposicao` | varchar | Identificador da proposição (Câmara) ou da matéria (Senado) na fonte; liga a fct_proposicoes (fonte e id_proposicao). O teste de aviso mede as que não estão carregadas lá. |  |
| `papel` | varchar | Papel da proposição na votação: afetada, objeto (Câmara) ou materia (Senado). |  |
| `id_captura` | bigint | Captura do arquivo de origem (URL, data e hash em metadata.capturas). |  |
| `dt_captura` | date | Data da captura do arquivo de origem. |  |

### marts.dim_constituicao_dispositivos

| Coluna | Tipo | Descrição | Dado pessoal |
| --- | --- | --- | --- |
| `parte` | varchar | Constituição (parte permanente) ou ADCT. |  |
| `ordem` | integer | Posição do parágrafo no arquivo, a partir de 1. |  |
| `tipo` | varchar | Cabeçalho do arquivo, preâmbulo, título, capítulo, seção, subseção, artigo, parágrafo, inciso, alínea, item, texto ou assinaturas. |  |
| `identificador` | varchar | Caminho do dispositivo (Art. 5º, § 1º, I, a)); vazio em títulos, capítulos e linhas sem artigo. |  |
| `artigo` | varchar | Número do artigo a que a linha pertence. |  |
| `paragrafo` | varchar | Número do parágrafo (ou único) a que a linha pertence. |  |
| `inciso` | varchar | Inciso (algarismo romano) a que a linha pertence. |  |
| `alinea` | varchar | Alínea (letra) a que a linha pertence. |  |
| `titulo` | varchar | Título (cabeçalho) em que a linha está. |  |
| `capitulo` | varchar | Capítulo (cabeçalho) em que a linha está. |  |
| `secao` | varchar | Seção (cabeçalho) em que a linha está. |  |
| `texto` | varchar | A linha inteira como a Câmara publica, com a indicação da emenda que a alterou. |  |
| `atualizada_ate_emenda` | integer | Número da emenda constitucional até a qual o arquivo está atualizado. |  |
| `fonte_url` | varchar | Página oficial da Câmara com o texto atualizado. |  |
| `dt_captura` | date | Data da captura do arquivo de origem. |  |
| `fonte` | varchar | Fonte oficial do registro. |  |
| `id_captura` | bigint | Captura do arquivo de origem (URL, data e hash em metadata.capturas). |  |

### marts.dim_disputas

| Coluna | Tipo | Descrição | Dado pessoal |
| --- | --- | --- | --- |
| `fonte` | varchar | Fonte oficial do registro (tse). |  |
| `id_disputa` | varchar | Chave da disputa: ano, código da eleição, código do cargo no TSE e unidade eleitoral. |  |
| `id_eleicao` | varchar | Eleição da disputa. |  |
| `id_cargo` | varchar | Cargo disputado. |  |
| `id_territorio` | varchar | Território da unidade eleitoral (país, UF ou município do IBGE); vazio quando o código de município do TSE não liga a um só município. O teste de aviso mede quantas disputas ficam assim. |  |
| `ue` | varchar | Unidade eleitoral como o TSE publica: sigla da UF, BR ou o código do município. Guardada para auditoria. |  |
| `ue_nome` | varchar | Nome da unidade eleitoral, com caixa padronizada. |  |
| `qtd_vagas` | integer | Número de vagas da disputa, como o TSE informa. |  |
| `dt_posse` | date | Data de posse como o arquivo de vagas do TSE informa; o campo não é confiável em todos os anos (issue 71) e não substitui a regra legal do cargo. |  |
| `id_captura` | bigint | Captura do arquivo de vagas de origem (URL, data e hash em metadata.capturas). |  |
| `dt_captura` | date | Data da captura do arquivo de origem. |  |

### marts.dim_eleicoes

| Coluna | Tipo | Descrição | Dado pessoal |
| --- | --- | --- | --- |
| `fonte` | varchar | Fonte oficial do registro (tse). |  |
| `id_eleicao` | varchar | Chave da eleição: ano e código do TSE (por exemplo, 2022-544). |  |
| `ano_eleicao` | integer | Ano da eleição. |  |
| `cd_eleicao` | integer | Código da eleição no TSE. |  |
| `nome` | varchar | Descrição da eleição, como o TSE informa. |  |
| `fl_ordinaria` | boolean | DERIVADO: verdadeiro quando o código cobre mais unidades eleitorais que os demais do ano em algum cargo (as suplementares e renovadas cobrem poucas). Regra do projeto, não informação do TSE. |  |
| `dt_primeiro_turno` | date | Dia do 1º turno do ano, como o TSE informa nos arquivos de candidaturas (a eleição geral e a municipal nunca caem no mesmo ano). |  |
| `dt_segundo_turno` | date | Dia do 2º turno do ano, quando houve disputa em 2º turno; vazio nos demais casos e em 2006, cujo arquivo de candidaturas não traz o 2º turno de presidente. Em 2020 vale o primeiro dia (29/11): o 2º turno de Macapá foi adiado para 20/12. |  |
| `id_captura` | bigint | Captura do arquivo de vagas de origem (URL, data e hash em metadata.capturas). |  |
| `dt_captura` | date | Data da captura do arquivo de origem. |  |

### marts.dim_frentes

| Coluna | Tipo | Descrição | Dado pessoal |
| --- | --- | --- | --- |
| `fonte` | varchar | Fonte oficial do registro. |  |
| `id_frente` | bigint | Identificador da frente na fonte. |  |
| `titulo` | varchar | Título da frente. |  |
| `dt_criacao` | date | Data de criação. |  |
| `id_legislatura` | integer | Legislatura em que foi criada. |  |
| `situacao` | varchar | Situação informada pela fonte. |  |
| `id_pessoa_coordenador` | bigint | Pessoa coordenadora (dim_pessoas_cadastro); vazia se a fonte não informa ou não é deputado. |  |
| `id_captura` | bigint | Captura do arquivo de origem (URL, data e hash em metadata.capturas). |  |
| `dt_captura` | date | Data da captura do arquivo de origem. |  |

### marts.dim_legislaturas

| Coluna | Tipo | Descrição | Dado pessoal |
| --- | --- | --- | --- |
| `fonte` | varchar | Fonte oficial do registro. |  |
| `id_legislatura` | integer | Número da legislatura. |  |
| `dt_inicio` | date | Início oficial da legislatura. |  |
| `dt_fim` | date | Fim oficial da legislatura. |  |
| `ano_eleicao` | integer | Ano da eleição que a formou. |  |
| `id_captura` | bigint | Captura do arquivo de origem (URL, data e hash em metadata.capturas). |  |
| `dt_captura` | date | Data da captura do arquivo de origem. |  |

### marts.dim_municipios

| Coluna | Tipo | Descrição | Dado pessoal |
| --- | --- | --- | --- |
| `fonte` | varchar | Fonte oficial do registro (ibge). |  |
| `id_municipio` | integer | Código do município no IBGE (7 dígitos). |  |
| `nome` | varchar | Nome do município, como o IBGE informa. |  |
| `uf` | varchar | Sigla da UF do município. |  |
| `uf_nome` | varchar | Nome da UF. |  |
| `regiao_sigla` | varchar | Sigla da grande região (N, NE, SE, S, CO). |  |
| `regiao_nome` | varchar | Nome da grande região. |  |
| `regiao_imediata` | varchar | Nome da região geográfica imediata do município. |  |
| `regiao_intermediaria` | varchar | Nome da região geográfica intermediária do município. |  |
| `nome_busca` | varchar | Nome sem acento e em minúsculas, para buscar. |  |
| `dt_captura` | date | Data da captura da lista de municípios. |  |
| `id_captura` | bigint | Captura do arquivo de origem (URL, data e hash em metadata.capturas). |  |

### marts.dim_municipios_codigos_tse

| Coluna | Tipo | Descrição | Dado pessoal |
| --- | --- | --- | --- |
| `fonte` | varchar | Fonte do código de município (tse). |  |
| `cd_municipio_tse` | varchar | Código do município no TSE (unidade eleitoral das eleições municipais). |  |
| `nome_tse` | varchar | Nome do município no TSE, da eleição mais recente em que aparece. |  |
| `uf` | varchar | Sigla da UF do município no TSE. |  |
| `id_municipio` | integer | Código do município no IBGE; vazio quando nome e UF não ligam a um só município. |  |
| `metodo` | varchar | Regra que ligou os dois códigos (nome e UF iguais e únicos); vazio sem ligação. |  |

### marts.dim_orgaos

| Coluna | Tipo | Descrição | Dado pessoal |
| --- | --- | --- | --- |
| `fonte` | varchar | Fonte oficial do registro (camara). |  |
| `id_orgao` | varchar | Chave do órgão no projeto: fonte e identificador da fonte. |  |
| `id_orgao_na_fonte` | bigint | Identificador do órgão na fonte. |  |
| `sigla` | varchar | Sigla do órgão. |  |
| `nome_curto` | varchar | Nome curto do órgão, como a fonte informa. |  |
| `nome` | varchar | Nome oficial do órgão. |  |
| `tipo` | varchar | Tipo do órgão segundo a fonte. |  |
| `casa` | varchar | Casa legislativa informada pela fonte; vazia quando não informa. |  |
| `situacao` | varchar | Situação do órgão segundo a fonte. |  |
| `dt_inicio` | date | Início do órgão, quando a fonte informa. |  |
| `dt_instalacao` | date | Data de instalação, quando a fonte informa. |  |
| `dt_fim` | date | Fim do órgão, quando a fonte informa. |  |
| `fonte_url` | varchar | Endereço do órgão na fonte oficial. |  |
| `id_captura` | bigint | Captura do arquivo de origem (URL, data e hash em metadata.capturas). |  |
| `dt_captura` | date | Data da captura do arquivo de origem. |  |

### marts.dim_partidos_camara

| Coluna | Tipo | Descrição | Dado pessoal |
| --- | --- | --- | --- |
| `fonte` | varchar | Fonte oficial do registro. |  |
| `id_partido` | bigint | Identificador do partido na fonte. |  |
| `sigla` | varchar | Sigla do partido sem os asteriscos que a Câmara põe depois dela; mais de um registro pode ter a mesma sigla (veja sigla_original). |  |
| `sigla_original` | varchar | Sigla exatamente como a Câmara publica, com os asteriscos (por exemplo, a mesma sigla com um, dois ou três asteriscos, registros diferentes). O significado dos asteriscos não consta nas fontes que consultamos. |  |
| `nome` | varchar | Nome do partido, com caixa padronizada. |  |
| `id_captura` | bigint | Captura do arquivo de origem (URL, data e hash em metadata.capturas). |  |
| `dt_captura` | date | Data da captura do arquivo de origem. |  |

### marts.dim_partidos_linhagem

| Coluna | Tipo | Descrição | Dado pessoal |
| --- | --- | --- | --- |
| `sigla_anterior` | varchar | Sigla do partido antes do evento, como aparece nos votos. |  |
| `sigla_posterior` | varchar | Sigla depois do evento (a do partido resultante, em fusão e incorporação). |  |
| `tipo` | varchar | Mudança de nome, fusão ou incorporação. |  |
| `dt_aprovacao` | date | Data da aprovação pelo TSE; vazia quando só o mês é conhecido. |  |
| `ano` | integer | Ano do evento. |  |
| `fonte_url` | varchar | Página oficial do TSE que registra o evento. |  |
| `observacao` | varchar | Divergência de data, resolução ou ressalva da fonte. |  |

### marts.dim_pessoas

| Coluna | Tipo | Descrição | Dado pessoal |
| --- | --- | --- | --- |
| `id_pessoa` | bigint | Chave própria e estável da pessoa (schema identity). |  |
| `nome_civil` | varchar | Nome civil, como a fonte publica, com caixa padronizada. |  |
| `fonte_nome_civil` | varchar | Fonte do nome civil (camara, senado ou tse). |  |
| `nome_publico` | varchar | Nome pelo qual a pessoa é conhecida: nome parlamentar ou, sem ele, nome de urna da candidatura mais recente. |  |
| `fonte_nome_publico` | varchar | Fonte do nome público. |  |
| `dt_nascimento` | date | Data de nascimento como a fonte publica; vazia quando nenhuma fonte informa. O TSE usa 1º de janeiro quando só conhece o ano. |  |
| `fonte_dt_nascimento` | varchar | Fonte da data de nascimento. |  |
| `genero` | varchar | Masculino ou feminino, só quando a fonte diz; vazio nos demais casos (inclusive dado protegido). |  |
| `fonte_genero` | varchar | Fonte do gênero. |  |
| `uf_nascimento` | varchar | UF de nascimento: a do cadastro da Câmara ou do Senado quando existe; senão, a declarada na candidatura mais recente do TSE que a informa (ZZ para nascido no exterior). |  |
| `fonte_uf_nascimento` | varchar | Fonte da UF de nascimento (camara, senado ou tse). |  |
| `escolaridade` | varchar | Escolaridade: a do cadastro da Câmara ou do Senado quando existe; senão, o grau de instrução declarado na candidatura mais recente do TSE que o informa (Não divulgável quando o TSE protege o dado). |  |
| `fonte_escolaridade` | varchar | Fonte da escolaridade (camara, senado ou tse). |  |
| `profissoes` | varchar | Profissões: as do cadastro da Câmara (separadas por ponto e vírgula) quando existem; senão, a ocupação declarada na candidatura mais recente do TSE que a informa. |  |
| `fonte_profissoes` | varchar | Fonte das profissões (camara, senado ou tse). |  |
| `estado_civil` | varchar | Estado civil declarado na candidatura mais recente do TSE que o informa; só o TSE tem (Não divulgável quando protege o dado). |  |
| `nome_social` | varchar | Nome social declarado na candidatura mais recente do TSE que o informa; vazio para quase todos (poucos declaram). |  |
| `foto_caminho` | varchar | Foto oficial do TSE da candidatura mais recente que a tem (caminho no lake público, coleção arq_fotos); vazia sem foto. |  |
| `id_captura_tse` | bigint | Captura do arquivo de candidaturas do TSE da candidatura mais recente da pessoa (URL, data e hash em metadata.capturas); vazia sem candidatura. |  |
| `dt_captura_tse` | date | Data dessa captura. |  |
| `dt_entrada` | date | Dia em que a pessoa entrou na identidade do projeto (para o eleito do TSE, a primeira execução depois da eleição). |  |

### marts.dim_pessoas_cadastro

| Coluna | Tipo | Descrição | Dado pessoal |
| --- | --- | --- | --- |
| `id_pessoa` | bigint | Chave própria e estável da pessoa (schema identity). |  |
| `fonte` | varchar | Fonte principal do cadastro da pessoa (camara ou senado). |  |
| `fontes` | varchar | Todas as fontes em que a pessoa aparece (por exemplo, camara, senado). |  |
| `nome` | varchar | Nome parlamentar, com caixa padronizada. |  |
| `nome_civil` | varchar | Nome civil, com caixa padronizada. |  |
| `nome_ordem` | varchar | Nome sem acento e em minúsculas, para ordenar. |  |
| `nome_busca` | varchar | Nome e nome civil sem acento, para buscar. |  |
| `sexo` | varchar | Sexo registrado no cadastro da fonte. |  |
| `dt_nascimento` | date | Data de nascimento informada pela fonte. |  |
| `dt_falecimento` | date | Data de falecimento informada pela fonte. |  |
| `municipio_nascimento` | varchar | Município de nascimento informado pela fonte. |  |
| `uf_nascimento` | varchar | UF de nascimento informada pela fonte. |  |
| `foto_url` | varchar | Endereço da foto oficial. |  |
| `rede_social_url` | varchar | Primeira rede social informada no cadastro. |  |
| `site_url` | varchar | Site informado no cadastro. |  |
| `escolaridade` | varchar | Escolaridade informada no cadastro da Câmara; vazia onde a fonte não informa (Senado). |  |
| `situacao_atual` | varchar | Situação no último status da Câmara (por exemplo, Exercício ou Licença); vazia onde a fonte não informa. |  |
| `condicao_eleitoral` | varchar | Titular ou suplente no último status da Câmara; vazia onde a fonte não informa. |  |
| `email_institucional` | varchar | E-mail institucional do gabinete, como a Câmara ou o Senado publica. |  |
| `telefone_institucional` | varchar | Telefone institucional do gabinete; no Senado, vários separados por ponto e vírgula. |  |
| `gabinete_endereco` | varchar | Endereço do gabinete (prédio, sala e andar na Câmara; endereço no Senado). |  |
| `pagina_url` | varchar | Página oficial da pessoa no Senado; vazia onde a fonte não informa. |  |
| `profissoes` | varchar | Profissões declaradas, separadas por ponto e vírgula. |  |
| `dt_captura` | date | Data da captura do cadastro de deputados. |  |
| `id_captura` | bigint | Captura do arquivo de origem (URL, data e hash em metadata.capturas). |  |

### marts.dim_territorios

| Coluna | Tipo | Descrição | Dado pessoal |
| --- | --- | --- | --- |
| `fonte` | varchar | Fonte oficial do registro (ibge). |  |
| `id_territorio` | varchar | Chave do território: BR para o país, o código do IBGE de 2 dígitos para a UF e o de 7 dígitos para o município. |  |
| `tipo` | varchar | Nível do território: pais, uf ou municipio. |  |
| `nome` | varchar | Nome do território, como o IBGE informa. |  |
| `sigla` | varchar | Sigla da UF (e BR para o país); vazia nos municípios. |  |
| `id_territorio_pai` | varchar | Território que contém este: a UF para o município e o país para a UF; vazio no país. |  |
| `regiao_sigla` | varchar | Sigla da grande região (N, NE, SE, S, CO); vazia no país. |  |
| `cd_municipio_tse` | varchar | Código do município no TSE (unidade eleitoral das eleições municipais); vazio quando nome e UF não ligam a um só município e fora dos municípios. |  |
| `id_captura` | bigint | Captura do arquivo de origem (URL, data e hash em metadata.capturas). |  |
| `dt_captura` | date | Data da captura do arquivo de origem. |  |

### marts.fct_campanhas

| Coluna | Tipo | Descrição | Dado pessoal |
| --- | --- | --- | --- |
| `fonte` | varchar | Fonte oficial do registro (tse). |  |
| `id_candidatura` | varchar | Candidatura (fct_candidaturas). 434 candidaturas com bens (2012, 2016, 2020 e 2024) são de eleições suplementares ou renovadas, que as candidaturas não trazem (issue 74); o teste de aviso mede essas. |  |
| `qtd_bens` | bigint | Quantidade de bens declarados; vazio se o candidato não declarou ou o arquivo não foi carregado. |  |
| `valor_bens` | decimal(18,2) | Soma dos valores dos bens declarados, em reais, sem correção. |  |
| `qtd_receitas` | bigint | Quantidade de receitas na prestação de contas; vazio se o arquivo não foi carregado ou não traz o candidato. |  |
| `valor_receitas` | decimal(18,2) | Soma das receitas declaradas, em reais. |  |
| `qtd_despesas` | bigint | Quantidade de despesas contratadas na prestação de contas; vazio se o arquivo não foi carregado ou não traz o candidato. |  |
| `valor_despesas` | decimal(18,2) | Soma das despesas contratadas declaradas, em reais. |  |
| `dt_prestacao` | date | Data mais recente da prestação de contas entre receitas e despesas. |  |
| `id_captura_bens` | bigint | Captura do arquivo de bens de origem; vazia sem bens. |  |
| `id_captura_receitas` | bigint | Captura do arquivo de receitas de origem; vazia sem receitas. |  |
| `id_captura_despesas` | bigint | Captura do arquivo de despesas de origem; vazia sem despesas. |  |
| `dt_captura` | date | Data da captura mais recente entre os arquivos de bens, receitas e despesas de origem; as capturas de cada arquivo estão em id_captura_bens, id_captura_receitas e id_captura_despesas. |  |

### marts.fct_candidaturas

| Coluna | Tipo | Descrição | Dado pessoal |
| --- | --- | --- | --- |
| `fonte` | varchar | Fonte oficial do registro (tse). |  |
| `id_candidatura` | varchar | Identificador da candidatura: ano da eleição, unidade eleitoral e sequencial do candidato, como o TSE informa. |  |
| `id_disputa` | varchar | Disputa da candidatura (dim_disputas); vazio quando o arquivo de vagas do TSE não traz a unidade do candidato. O teste de aviso mede quantas ficam assim. |  |
| `id_eleicao` | varchar | Eleição da candidatura (dim_eleicoes), achada pelo ano e pelo código da eleição do arquivo de candidaturas, sem depender da disputa. Vazia quando o arquivo de vagas não traz essa eleição; o teste de aviso mede quantas. |  |
| `sq_candidato` | bigint | Número sequencial do candidato na eleição, como o TSE informa; liga ao nome do arquivo de foto. |  |
| `numero` | varchar | Número do candidato na urna. |  |
| `numero_partido` | varchar | Número do partido na urna, como o TSE informa. Não identifica o partido ao longo do tempo: o mesmo número já foi usado por partidos diferentes (por exemplo, um número foi de um partido e depois de outro). |  |
| `nome` | varchar | Nome civil do candidato, com caixa padronizada. |  |
| `nome_urna` | varchar | Nome de urna, com caixa padronizada. |  |
| `nome_social` | varchar | Nome social declarado pelo candidato; o TSE às vezes repete o nome civil ou grava Não divulgável (dado protegido). | sim |
| `genero` | varchar | Gênero do candidato, como o TSE informa. |  |
| `grau_instrucao` | varchar | Grau de instrução declarado; Não divulgável quando o TSE protege o dado. | sim |
| `estado_civil` | varchar | Estado civil declarado na candidatura; Não divulgável quando o TSE protege o dado. | sim |
| `ocupacao` | varchar | Ocupação declarada, como o TSE informa; Não divulgável quando o TSE protege o dado. |  |
| `uf_nascimento` | varchar | UF de nascimento declarada na candidatura, como o TSE informa (ZZ para nascido no exterior); vazia quando o TSE não informa. |  |
| `id_partido` | integer | Partido da candidatura (dim_partidos), achado pela sigla, pelo número e pelo ano da eleição em partidos_siglas, nunca só pelo número. Vazio quando a combinação não foi curada; o teste de aviso mede quantas. |  |
| `partido` | varchar | Sigla do partido na eleição, como o TSE informa. |  |
| `partido_nome` | varchar | Nome do partido na eleição. |  |
| `federacao` | varchar | Sigla da federação partidária (desde 2022); vazia nos anos anteriores. |  |
| `coligacao` | varchar | Nome da coligação da candidatura; vazio sem coligação. |  |
| `dt_eleicao` | date | Dia da votação do último turno que a candidatura disputou, como o TSE informa (DT_ELEICAO). |  |
| `situacao_candidatura` | varchar | Situação da candidatura no último turno em que consta, como o TSE informa (por exemplo, deferido, indeferido). |  |
| `qtd_turnos` | integer | Número do último turno em que a candidatura consta (2 quando foi ao segundo turno). |  |
| `resultado` | varchar | Resultado do último turno como o arquivo de candidaturas do TSE informa (eleito, suplente, não eleito, 2º turno); vazio quando o TSE não informa, como o 2º turno de presidente de 2006. |  |
| `fl_eleito` | boolean | Verdadeiro quando a candidatura foi eleita: o TSE informa (fl_eleito_informado) ou, sem essa informação, a Constituição deriva dos votos (base_eleicao). Mesmo conjunto de fct_mandatos. O texto original do TSE segue em resultado. Vazio quando o TSE não informa o resultado e nada foi derivado. |  |
| `fl_eleito_informado` | boolean | Verdadeiro quando o TSE marca a candidatura como eleita em algum turno (só o informado; era o significado de fl_eleito até a mudança). Falso não quer dizer derrota quando o resultado está vazio. |  |
| `base_eleicao` | varchar | Como se sabe que a candidatura foi eleita: informado pelo TSE ou DERIVADO dos votos pela Constituição (int_tse_eleitos). Vazia para quem não foi eleito. Quando preenchida, fl_eleito é verdadeiro; fl_eleito_informado segue só o resultado do TSE. |  |
| `fl_mais_votado_no_ultimo_turno` | boolean | DERIVADO dos votos, não é resultado do TSE: só para presidente, governador e prefeito, verdadeiro se teve mais votos válidos no último turno com votos. Vazio sem votos carregados ou em cargo de várias vagas. |  |
| `id_pessoa_tse` | varchar | Identificador da mesma pessoa entre as eleições do TSE (nome civil ou de urna e data de nascimento únicos, ADRs 0025 e 0026); vazio sem ligação, o que não quer dizer novato. |  |
| `id_pessoa` | bigint | Pessoa do projeto (dim_pessoas) quando a candidatura é de alguém eleito alguma vez ou que foi deputado ou senador (ligada pelo nome e o nascimento); vazio para quem nunca foi eleito, por regra (ADR 0031). |  |
| `foto_arquivo` | varchar | Nome do arquivo da foto oficial no pacote do TSE; vazio quando o pacote não traz foto do candidato. |  |
| `foto_caminho` | varchar | Caminho da foto na raiz do lake público, na coleção arq_fotos do TSE (ano, UF do pacote e sequencial; ADR 0037); vazio sem foto. |  |
| `foto_pacote_url` | varchar | Endereço oficial do pacote de fotos do TSE que contém a foto. |  |
| `id_captura` | bigint | Captura do arquivo de candidaturas de origem (URL, data e hash em metadata.capturas). |  |
| `dt_captura` | date | Data da captura do arquivo de origem. |  |

### marts.fct_candidaturas_bens

| Coluna | Tipo | Descrição | Dado pessoal |
| --- | --- | --- | --- |
| `fonte` | varchar | Fonte oficial do registro. |  |
| `id_pessoa` | bigint | Chave da pessoa (dim_pessoas_cadastro). |  |
| `id_candidatura` | varchar | Candidatura (fct_candidaturas): ano da eleição e sequencial do candidato. |  |
| `ano_eleicao` | integer | Ano da eleição. |  |
| `ordem` | integer | Número do bem na declaração do candidato. |  |
| `tipo` | varchar | Tipo do bem (imóvel, veículo, aplicação financeira etc.). |  |
| `descricao` | varchar | Descrição do bem, como o candidato declarou. CPF (***.nnn.nnn-**) é mascarado pelo projeto; o original fica no landing. Agência e conta bancária que o candidato escreveu na descrição vêm como a fonte publica, sem máscara (ADR 0050, issue 289; a republicação desta tabela é do fundador). |  |
| `valor` | decimal(18,2) | Valor declarado em reais, sem correção. |  |
| `dt_atualizacao` | date | Data da última atualização do bem na declaração. |  |
| `dt_captura` | date | Data da captura do arquivo de origem. |  |
| `id_captura` | bigint | Captura do arquivo de origem (URL, data e hash em metadata.capturas). |  |

### marts.fct_candidaturas_votos

| Coluna | Tipo | Descrição | Dado pessoal |
| --- | --- | --- | --- |
| `fonte` | varchar | Fonte oficial do registro. |  |
| `id_pessoa` | bigint | Chave da pessoa (dim_pessoas_cadastro). |  |
| `id_candidatura` | varchar | Candidatura (fct_candidaturas). |  |
| `ano_eleicao` | integer | Ano da eleição. |  |
| `turno` | integer | Turno da eleição. |  |
| `uf` | varchar | UF da candidatura. |  |
| `cargo` | varchar | Cargo disputado. |  |
| `votos_nominais` | bigint | Votos nominais recebidos, de qualquer destinação. |  |
| `votos_validos` | bigint | Votos nominais válidos. |  |
| `municipios` | bigint | Em quantos municípios o candidato teve votos. |  |
| `dt_captura` | date | Data da captura do arquivo de origem. |  |
| `id_captura` | bigint | Captura do arquivo de origem (URL, data e hash em metadata.capturas). |  |

### marts.fct_cargos_ocupacoes

| Coluna | Tipo | Descrição | Dado pessoal |
| --- | --- | --- | --- |
| `id_ocupacao` | varchar | Identificador do período: a base (exercicio ou mandato) e o identificador do exercício ou da candidatura de origem. |  |
| `fonte` | varchar | Fonte oficial do registro de origem (camara e senado para o exercício; tse para o mandato). |  |
| `id_pessoa` | bigint | Pessoa que ocupa o cargo (dim_pessoas). |  |
| `id_cargo` | varchar | Cargo ocupado (dim_cargos); vazio no mandato de candidatura sem disputa (o teste de aviso mede). |  |
| `id_territorio` | varchar | Território do cargo (dim_territorios); vazio onde a fonte não liga a um território (o teste de aviso mede). |  |
| `id_partido` | integer | Partido da pessoa na ocupação (dim_partidos). Por ordem: o da candidatura do TSE (o mandato), o informado pelo histórico da Câmara e o derivado do último registro (fct_exercicios); base_partido diz qual. Vazio sem registro de partido (o teste de aviso mede). |  |
| `base_partido` | varchar | informado (candidatura do TSE ou histórico da Câmara) ou derivado (último partido registrado da pessoa até o ano do início). Vazia quando id_partido é vazio. |  |
| `id_candidatura` | varchar | Mandato eleito (fct_mandatos) a que a ocupação pertence; vazio para o suplente que assumiu e para o eleito em eleição suplementar. |  |
| `id_exercicio` | varchar | Exercício publicado (fct_exercicios) que originou a ocupação; vazio quando a ocupação vem só do mandato. |  |
| `ano_inicio` | integer | Ano em que a ocupação começa: o do exercício, ou o ano seguinte ao da eleição no mandato. Preenchido mesmo sem dt_inicio. |  |
| `dt_inicio` | date | Dia do início; vazio quando o dia não está numa fonte nem numa regra (por exemplo, deputado estadual de 2026, que depende da constituição de cada estado). |  |
| `base_dt_inicio` | varchar | informado (a fonte do exercício, ou a data de posse do TSE onde a Constituição não fixa a data) ou derivado (regra da Constituição para o cargo). Vazia quando dt_inicio é vazio. |  |
| `dt_fim` | date | Fim da ocupação: o fim real do exercício quando a fonte o registra, senão o fim do mandato, previsto pela duração do cargo. Vazio quando o início é vazio. Com dt_inicio, diz quem ocupa o cargo em uma data. |  |
| `base_dt_fim` | varchar | informado (a Câmara ou o Senado registra o fim do exercício) ou previsto (fim do mandato pela duração do cargo, sem cassação, renúncia nem morte). Vazia quando dt_fim é vazio. |  |
| `base_ocupacao` | varchar | exercicio (período em que a Câmara ou o Senado registra a pessoa em exercício) ou mandato (período da eleição, sem exercício publicado). |  |
| `id_captura` | bigint | Captura do arquivo de origem (URL, data e hash em metadata.capturas). |  |
| `dt_captura` | date | Data da captura do arquivo de origem. |  |

### marts.fct_constituicao_alteracoes

| Coluna | Tipo | Descrição | Dado pessoal |
| --- | --- | --- | --- |
| `parte` | varchar | Constituição (parte permanente) ou ADCT. |  |
| `ordem` | integer | Posição do parágrafo no arquivo (dim_constituicao_dispositivos). |  |
| `identificador` | varchar | Caminho do dispositivo (dim_constituicao_dispositivos). |  |
| `tipo_alteracao` | varchar | Tirado das palavras da nota: redação dada, incluído, revogado, suprimido, renumerado, vide (só referência) ou outra. |  |
| `emenda_tipo` | varchar | Emenda Constitucional ou Emenda Constitucional de Revisão. |  |
| `emenda_numero` | integer | Número da emenda citada na nota. |  |
| `emenda_ano` | integer | Ano da emenda; só quando a nota cita uma emenda. |  |
| `nota` | varchar | A nota como o texto publica, sem os parênteses. |  |
| `fonte` | varchar | Fonte oficial do registro. |  |
| `id_captura` | bigint | Captura do arquivo de origem (URL, data e hash em metadata.capturas). |  |
| `dt_captura` | date | Data da captura do arquivo de origem. |  |

### marts.fct_emendas

| Coluna | Tipo | Descrição | Dado pessoal |
| --- | --- | --- | --- |
| `fonte` | varchar | Fonte oficial do registro. |  |
| `cd_emenda` | varchar | Identificador da emenda, de 12 dígitos: 4 do ano da emenda, 4 do código do autor e 4 do número da emenda do autor (dicionário de dados do portal); vazio em registros antigos sem código. |  |
| `ano` | integer | Ano da emenda. |  |
| `tipo` | varchar | Tipo da emenda (individual, de bancada, de comissão, de relator). |  |
| `cd_autor` | varchar | Código do autor da emenda como registrado no SIAFI (não é o código do parlamentar); vazio quando a fonte não informa. |  |
| `autor_nome` | varchar | Nome do autor da emenda como registrado no SIAFI (parlamentar, bancada, comissão ou relator-geral), com caixa padronizada. |  |
| `id_pessoa` | bigint | Pessoa autora, DERIVADA (não vem da fonte): só em emenda individual cujo nome do autor é o nome parlamentar ou civil de uma só pessoa com mandato federal no ano da emenda ou no anterior; vazia em emenda de bancada, comissão ou relator, sem autor, sem correspondência ou ambígua. |  |
| `regra_ligacao_pessoa` | varchar | Regra que ligou a pessoa: nome_parlamentar_e_exercicio ou nome_civil_e_exercicio (ADR 0056); vazia quando id_pessoa é vazio. |  |
| `precisao_ligacao_pessoa` | varchar | Precisão do vínculo: derivada (inferida por regra, sem identificador oficial); vazia quando id_pessoa é vazio. |  |
| `numero` | varchar | Número da emenda. |  |
| `localidade` | varchar | Atributo do Plano de Trabalho que indica a região onde a despesa ocorre, como a fonte informa. |  |
| `municipio_ibge` | integer | Código IBGE do município de destinação do recurso; pode estar em branco, conforme a localidade de aplicação. |  |
| `municipio` | varchar | Município de aplicação. |  |
| `uf` | varchar | UF de aplicação, como a fonte informa. |  |
| `regiao` | varchar | Região. |  |
| `funcao` | varchar | Função orçamentária. |  |
| `subfuncao` | varchar | Subfunção orçamentária. |  |
| `cd_programa` | varchar | Código do programa. |  |
| `programa` | varchar | Programa. |  |
| `cd_acao` | varchar | Código da ação. |  |
| `acao` | varchar | Ação orçamentária. |  |
| `plano_orcamentario` | varchar | Plano orçamentário. |  |
| `valor_empenhado` | decimal(18,2) | Valor empenhado em reais. |  |
| `valor_liquidado` | decimal(18,2) | Valor liquidado em reais. |  |
| `valor_pago` | decimal(18,2) | Valor pago em reais. |  |
| `valor_restos_a_pagar_inscritos` | decimal(18,2) | Restos a pagar inscritos em reais. |  |
| `valor_restos_a_pagar_cancelados` | decimal(18,2) | Restos a pagar cancelados em reais. |  |
| `valor_restos_a_pagar_pagos` | decimal(18,2) | Restos a pagar pagos em reais. |  |
| `dt_captura` | date | Data da captura do arquivo de origem. |  |
| `id_captura` | bigint | Captura do arquivo de origem (URL, data e hash em metadata.capturas). |  |

### marts.fct_emendas_convenios

| Coluna | Tipo | Descrição | Dado pessoal |
| --- | --- | --- | --- |
| `fonte` | varchar | Fonte oficial do registro. |  |
| `cd_emenda` | varchar | Código da emenda (fct_emendas). |  |
| `funcao` | varchar | Função orçamentária. |  |
| `subfuncao` | varchar | Subfunção orçamentária. |  |
| `localidade` | varchar | Localidade do gasto, como a fonte informa. |  |
| `tipo` | varchar | Tipo da emenda. |  |
| `dt_publicacao` | date | Data de publicação do convênio. |  |
| `convenente` | varchar | Quem recebe os recursos do Governo Federal: órgão ou entidade pública de qualquer esfera de governo, ou organização particular com a qual a administração federal pactua o convênio. |  |
| `objeto` | varchar | O que foi pactuado entre o concedente federal e o convenente. |  |
| `convenio_numero` | varchar | Número do convênio. |  |
| `valor` | decimal(18,2) | Valor do convênio em reais: a participação do concedente, somada à parcela de rendimento de aplicação financeira (código 999), quando houver. |  |
| `dt_captura` | date | Data da captura do arquivo de origem. |  |
| `id_captura` | bigint | Captura do arquivo de origem (URL, data e hash em metadata.capturas). |  |

### marts.fct_emendas_favorecidos

| Coluna | Tipo | Descrição | Dado pessoal |
| --- | --- | --- | --- |
| `fonte` | varchar | Fonte oficial do registro. |  |
| `cd_emenda` | varchar | Código da emenda (fct_emendas). |  |
| `cd_autor` | varchar | Código do autor da emenda como registrado no SIAFI (não é o código do parlamentar); vazio quando a fonte não informa. |  |
| `autor_nome` | varchar | Nome do autor da emenda como registrado no SIAFI (parlamentar, bancada, comissão ou relator-geral), com caixa padronizada. |  |
| `numero` | varchar | Número da emenda. |  |
| `tipo` | varchar | Tipo da emenda. |  |
| `ano` | integer | Ano do pagamento. |  |
| `mes` | integer | Mês do pagamento. |  |
| `cd_favorecido` | varchar | CNPJ, código da unidade gestora ou CPF mascarado do favorecido. A fonte já mascara o CPF; quando vem com 11 dígitos, o projeto mascara (***.nnn.nnn-**); o original fica no landing. | sim |
| `favorecido` | varchar | Nome do favorecido (pessoa física inclusive). Número de CPF de 11 dígitos no texto é mascarado (***.nnn.nnn-**) pelo projeto; o original fica no landing. | sim |
| `natureza_juridica` | varchar | Natureza jurídica do favorecido. |  |
| `tipo_favorecido` | varchar | Tipo do favorecido como a fonte informa: Pessoa Jurídica, Pessoa Fisica, Unidade Gestora, Inscrição Genérica, Sem informação ou Inválido (o dicionário do portal cita só pessoa física e jurídica; em parte das linhas a fonte grafa Inscrição Genéric, truncado). |  |
| `uf` | varchar | UF do favorecido. |  |
| `municipio` | varchar | Município do favorecido. |  |
| `valor` | decimal(18,2) | Valor recebido pelo favorecido em reais. |  |
| `fl_contem_dado_pessoal` | boolean | Verdadeiro quando a linha identifica uma pessoa física (CPF mascarado, tipo pessoa física ou inscrição genérica). |  |
| `dt_captura` | date | Data da captura do arquivo de origem. |  |
| `id_captura` | bigint | Captura do arquivo de origem (URL, data e hash em metadata.capturas). |  |

### marts.fct_eventos

| Coluna | Tipo | Descrição | Dado pessoal |
| --- | --- | --- | --- |
| `id_evento` | varchar | Tipo, fato de origem e identificador do registro de origem. |  |
| `id_pessoa` | bigint | Pessoa do evento (dim_pessoas). |  |
| `id_tipo_evento` | varchar | Tipo do evento, do catálogo fechado dim_evento_tipos. |  |
| `fato_origem` | varchar | Fato do qual o evento nasceu; precisa ser o fato_origem do tipo no catálogo. |  |
| `id_fato_origem` | varchar | Identificador do registro no fato de origem. |  |
| `ano_evento` | bigint | Ano do evento. |  |
| `dt_evento` | date | Dia do evento, só quando a fonte dá o dia; vazio quando só se conhece o ano (eleição, candidatura, nascimento só com o ano). |  |
| `id_disputa` | varchar | Disputa do evento (dim_disputas), quando o tipo exige. |  |
| `id_cargo` | varchar | Cargo do evento (dim_cargos), quando o tipo exige. |  |
| `id_territorio` | varchar | Território do evento (dim_territorios), quando o tipo exige. |  |
| `id_partido` | integer | Partido do evento (dim_partidos), quando o tipo exige. |  |
| `base` | varchar | Como o evento é obtido: informado pela fonte ou derivado de regra do projeto. |  |
| `id_captura` | bigint | Captura do arquivo de origem (URL, data e hash em metadata.capturas); vazia quando o evento vem de outra tabela do projeto. |  |
| `fonte` | varchar | Fonte oficial do fato de origem (tse, camara ou senado), pela captura; no nascimento e no falecimento, a fonte do cadastro que informa a data. O teste de aviso mede o que ficar sem. |  |
| `dt_captura` | date | Data da captura do arquivo de origem do fato; vazia quando o evento não tem id_captura. |  |

### marts.fct_exercicios

| Coluna | Tipo | Descrição | Dado pessoal |
| --- | --- | --- | --- |
| `fonte` | varchar | Fonte oficial do registro (camara ou senado). |  |
| `id_exercicio` | varchar | Identificador do período: fonte e identificador da fonte (Câmara: deputado, legislatura e momento da entrada). |  |
| `id_territorio` | varchar | Território representado (dim_territorios): a UF que a fonte informa, ligada pela sigla. Vazio quando a fonte não informa a UF (o teste de aviso mede). |  |
| `id_candidatura` | varchar | DERIVADO: o mandato (fct_mandatos) que o período cumpre, o da mesma pessoa e cargo cuja janela contém o início do período, com 31 dias de folga antes da posse para o registro. Vazio para o suplente e para o eleito em eleição suplementar, que não têm mandato eleito. |  |
| `id_partido` | integer | Partido da pessoa no início do período (dim_partidos); base_partido diz se é informado ou derivado. Vazio quando nenhum registro de partido da pessoa vale até o ano do início (o teste de aviso mede). |  |
| `base_partido` | varchar | informado: o partido do histórico da Câmara que cobre o início do período. derivado: o último partido registrado da pessoa até o ano do início (fct_pessoas_partidos); vale para o Senado, que não publica o partido do exercício. Vazia quando id_partido é vazio. |  |
| `id_pessoa` | bigint | Pessoa do projeto (dim_pessoas_cadastro); vazio se a ligação não existe (o teste de aviso mede). |  |
| `id_cargo` | varchar | Cargo exercido (dim_cargos): deputado_federal ou senador (suplente em exercício ocupa a vaga do titular). |  |
| `condicao_na_fonte` | varchar | Condição como a fonte informa (Câmara: Titular, Suplente, Efetivado; Senado: Titular, 1º Suplente, 2º Suplente); vazia quando a fonte não informa. |  |
| `id_legislatura` | integer | Legislatura do período, só na Câmara; vazia no Senado, onde o mandato dura oito anos. |  |
| `uf` | varchar | UF representada, como a fonte informa. |  |
| `dt_inicio` | date | Início do período, como a fonte informa. |  |
| `dt_fim` | date | Fim do período; vazio enquanto está em exercício. |  |
| `dt_mandato_fim` | date | Fim do mandato a que o período pertence, como a fonte publica: no Senado, o do mandato do titular (inclusive de quem assume como suplente); na Câmara, o fim da legislatura. Diferente de dt_fim, que é o fim do período de exercício. |  |
| `causa_fim` | varchar | Causa do fim do período, como a fonte informa (licença, renúncia, término do mandato); vazia se não informada ou em curso. |  |
| `id_captura` | bigint | Captura do arquivo de origem (URL, data e hash em metadata.capturas). |  |
| `dt_captura` | date | Data da captura do arquivo de origem. |  |

### marts.fct_licitacoes

| Coluna | Tipo | Descrição | Dado pessoal |
| --- | --- | --- | --- |
| `fonte` | varchar | Fonte oficial do registro. |  |
| `id_licitacao` | varchar | Chave da licitação montada pelo projeto: código da unidade gestora, código da modalidade e número da licitação, separados por hífen. Liga os itens, participantes e empenhos. |  |
| `numero` | varchar | Número da licitação no SIASG, como a fonte informa (único só junto com a unidade gestora e a modalidade). |  |
| `cd_ug` | varchar | Código SIAFI da unidade gestora responsável pela licitação. |  |
| `ug` | varchar | Nome da unidade gestora responsável pela licitação. |  |
| `cd_modalidade` | varchar | Código da modalidade de compra, como a fonte informa (01 convite, 02 tomada de preços, 03 concorrência, 05 pregão, 06 dispensa, 07 inexigibilidade, entre outros do dicionário do portal). |  |
| `modalidade` | varchar | Modalidade de compra, como a fonte informa. |  |
| `numero_processo` | varchar | Número do processo administrativo da licitação, como a fonte informa. |  |
| `objeto` | varchar | Objeto da licitação, texto livre da fonte (CPF no texto é mascarado (***.nnn.nnn-**) pelo projeto; o original fica no landing). |  |
| `situacao` | varchar | Situação da licitação, como a fonte informa (por exemplo, Publicado, Encerrado). |  |
| `cd_orgao_superior` | varchar | Código SIAFI do órgão superior (ministério ou equivalente). |  |
| `orgao_superior` | varchar | Nome do órgão superior. |  |
| `cd_orgao` | varchar | Código SIAFI do órgão da unidade gestora. |  |
| `orgao` | varchar | Nome do órgão da unidade gestora. |  |
| `uf` | varchar | UF da unidade gestora. |  |
| `municipio` | varchar | Município da unidade gestora. |  |
| `dt_resultado` | date | Data do resultado da compra (homologação publicada no Diário Oficial da União, segundo o dicionário do portal). |  |
| `dt_abertura` | date | Data de abertura para envio de propostas; vazia onde a fonte não informa. |  |
| `valor` | decimal(18,4) | Valor total licitado, em reais, com as quatro casas que a fonte publica. |  |
| `id_captura` | bigint | Captura do arquivo de origem (URL, data e hash em metadata.capturas). |  |
| `dt_captura` | date | Data da captura do arquivo de origem. |  |

### marts.fct_licitacoes_itens

| Coluna | Tipo | Descrição | Dado pessoal |
| --- | --- | --- | --- |
| `fonte` | varchar | Fonte oficial do registro. |  |
| `id_licitacao` | varchar | Licitação do item (fct_licitacoes). |  |
| `cd_item` | varchar | Código do item da compra (22 dígitos: unidade gestora, modalidade, número da licitação no ano, ano e sequencial do item, segundo o dicionário do portal); vazio em parte das linhas da fonte. |  |
| `item` | varchar | Descrição do item, texto livre da fonte (CPF no texto é mascarado pelo projeto). |  |
| `quantidade` | decimal(18,4) | Quantidade do item, com as quatro casas que a fonte publica. |  |
| `valor` | decimal(18,4) | Valor total do item, em reais, com as quatro casas que a fonte publica. |  |
| `cd_vencedor` | varchar | CNPJ do vencedor, como a fonte publica. CPF (11 dígitos, completo na fonte) sai mascarado (***.nnn.nnn-**) pelo projeto; o original fica no landing. | sim |
| `vencedor` | varchar | Nome do vencedor (pessoa física inclusive), como a fonte publica; número de CPF no texto é mascarado pelo projeto. | sim |
| `fl_contem_dado_pessoal` | boolean | Verdadeiro quando o vencedor é pessoa física (código com CPF mascarado). |  |
| `id_captura` | bigint | Captura do arquivo de origem (URL, data e hash em metadata.capturas). |  |
| `dt_captura` | date | Data da captura do arquivo de origem. |  |

### marts.fct_licitacoes_participantes

| Coluna | Tipo | Descrição | Dado pessoal |
| --- | --- | --- | --- |
| `fonte` | varchar | Fonte oficial do registro. |  |
| `id_licitacao` | varchar | Licitação do item (fct_licitacoes). |  |
| `cd_item` | varchar | Código do item da compra (liga a fct_licitacoes_itens); vazio em parte das linhas da fonte. |  |
| `item` | varchar | Descrição do item, texto livre da fonte (CPF no texto é mascarado pelo projeto). |  |
| `cd_participante` | varchar | Código do participante: CNPJ na maioria das linhas; a fonte traz também CPF (sai mascarado, ***.nnn.nnn-**) e códigos curtos que o dicionário do portal não descreve. Como a fonte publica. | sim |
| `participante` | varchar | Nome do participante (pessoa física inclusive), como a fonte publica; número de CPF no texto é mascarado pelo projeto. | sim |
| `fl_vencedor` | boolean | Verdadeiro quando o participante venceu o item (SIM na fonte); falso quando não (NÃO). |  |
| `fl_contem_dado_pessoal` | boolean | Verdadeiro quando o participante é pessoa física (código com CPF mascarado). |  |
| `id_captura` | bigint | Captura do arquivo de origem (URL, data e hash em metadata.capturas). |  |
| `dt_captura` | date | Data da captura do arquivo de origem. |  |

### marts.fct_mandatos

| Coluna | Tipo | Descrição | Dado pessoal |
| --- | --- | --- | --- |
| `fonte` | varchar | Fonte oficial do registro (tse). |  |
| `id_candidatura` | varchar | Candidatura eleita que originou o mandato (fct_candidaturas); identifica o mandato. |  |
| `id_disputa` | varchar | Disputa em que foi eleito (dim_disputas); vazio nas candidaturas sem disputa (o teste de aviso mede). |  |
| `id_eleicao` | varchar | Eleição (dim_eleicoes). |  |
| `id_cargo` | varchar | Cargo do mandato (dim_cargos). |  |
| `id_territorio` | varchar | Território do mandato (dim_territorios); vazio onde o TSE não liga a um território. |  |
| `id_partido` | integer | Partido pelo qual foi eleito (dim_partidos). |  |
| `base_eleicao` | varchar | Como se sabe que foi eleito: informado pelo TSE ou DERIVADO dos votos pela Constituição (disputa de uma vaga de eleição passada em que o TSE não informa o vencedor, como o 2º turno de presidente de 2006). |  |
| `id_pessoa_tse` | varchar | Identificador da pessoa entre as eleições do TSE; vazio sem ligação. |  |
| `id_pessoa` | bigint | Pessoa do projeto (dim_pessoas); todo eleito tem. O teste de aviso mede os que ficaram sem. |  |
| `dt_posse_tse` | date | Data de posse exatamente como o TSE informa na disputa, mesmo quando impossível (por exemplo, antes da eleição); guardada para auditoria. |  |
| `dt_inicio` | date | Início do mandato. Derivado da Constituição com a vigência por ano de eleição (dim_cargos_posse) ou da constituição estadual por UF (dim_cargos_posse_uf) onde elas fixam a data; sem regra (vereador, deputado estadual de UF sem fonte conferida), a data de posse do TSE quando cai no ano seguinte ao da eleição e a eleição não é a do ano corrente. Vazio nos demais casos. |  |
| `base_dt_inicio` | varchar | Como dt_inicio foi obtida: derivado (regra da Constituição ou da constituição estadual, com artigo e vigência em dim_cargos_posse e dim_cargos_posse_uf) ou informado (data do TSE, só onde a Constituição não fixa a data). Vazio quando dt_inicio é vazio. |  |
| `dt_fim_prevista` | date | DERIVADO: dt_inicio mais a duração do cargo na Constituição, menos um dia. É o fim previsto, não o fim real (cassação, renúncia e morte não entram). |  |
| `id_captura` | bigint | Captura do arquivo de candidaturas de origem (URL, data e hash em metadata.capturas). |  |
| `dt_captura` | date | Data da captura do arquivo de origem. |  |
| `ano_inicio` | integer | DERIVADO: ano da eleição (dim_eleicoes) mais um, o ano em que o mandato começa pela Constituição e pelas eleições ordinárias; preenchido mesmo sem data de posse. Vazio só quando a disputa não tem eleição (o teste de aviso mede). |  |
| `tipo_mandato` | varchar | DERIVADO, comparando com o mandato anterior da mesma pessoa no mesmo cargo (e na mesma unidade, abaixo do nível federal): reeleito (o anterior é da eleição de um mandato atrás), retorno (houve intervalo) ou novato (não há anterior e a base de eleições já cobria o ciclo anterior). Vazio quando não há prova: sem prova nada é afirmado. |  |

### marts.fct_normas

| Coluna | Tipo | Descrição | Dado pessoal |
| --- | --- | --- | --- |
| `fonte` | varchar | Fonte oficial do registro. |  |
| `id_norma` | bigint | Código da norma no Senado. |  |
| `tipo_sigla` | varchar | Sigla do tipo da norma na fonte (LEI-n, DEC-n, MPV-cs...). |  |
| `tipo` | varchar | Tipo da norma (lei numerada, decreto numerado, decreto legislativo etc.). |  |
| `numero` | varchar | Número da norma, como a fonte informa (pode ter letra). |  |
| `ano` | integer | Ano de assinatura. |  |
| `dt_assinatura` | date | Data de assinatura; vazia quando a fonte não informa. |  |
| `nome` | varchar | Nome oficial (por exemplo, Lei nº 14.116 de 31/12/2020). |  |
| `identificador` | varchar | Identificador curto da norma na fonte (LEI-14116-2020-12-31). |  |
| `ementa` | varchar | Ementa com caixa padronizada. |  |
| `ementa_oficial` | varchar | Ementa exatamente como a fonte publica. |  |
| `apelido` | varchar | Apelido popular quando a fonte informa (por exemplo, Lei de Diretrizes Orçamentárias - LDO 2021). |  |
| `fonte_url` | varchar | Página oficial da norma no Senado. |  |
| `dt_captura` | date | Data da captura do arquivo de origem. |  |
| `id_captura` | bigint | Captura do arquivo de origem (URL, data e hash em metadata.capturas). |  |

### marts.fct_normas_geradas

| Coluna | Tipo | Descrição | Dado pessoal |
| --- | --- | --- | --- |
| `fonte` | varchar | Fonte oficial do registro. |  |
| `id_proposicao` | varchar | Matéria (fct_proposicoes, junto com a fonte). |  |
| `id_norma` | bigint | Código da norma no Senado (fct_normas). |  |
| `tipo` | varchar | Tipo da norma (lei, emenda constitucional, decreto legislativo etc.). |  |
| `numero` | integer | Número da norma. |  |
| `ano` | integer | Ano de assinatura da norma. |  |
| `dt_assinatura` | date | Data de assinatura. |  |
| `dt_publicacao` | date | Data de publicação. |  |
| `descricao` | varchar | Descrição oficial da norma. |  |
| `veiculo_publicacao` | varchar | Veículo de publicação (por exemplo, DOU). |  |
| `dt_captura` | date | Data da captura do lote de origem. |  |
| `id_captura` | bigint | Captura do arquivo de origem (URL, data e hash em metadata.capturas). |  |

### marts.fct_normas_publicacoes

| Coluna | Tipo | Descrição | Dado pessoal |
| --- | --- | --- | --- |
| `fonte` | varchar | Fonte oficial do registro. |  |
| `id_norma` | bigint | Norma publicada (fct_normas). |  |
| `id_publicacao` | bigint | Código da publicação no Senado. |  |
| `tipo_sigla` | varchar | Tipo da publicação (PUB original, VEP veto parcialmente rejeitado etc.). |  |
| `veiculo` | varchar | Veículo e edição, como a fonte informa. |  |
| `dt_publicacao` | date | Data da publicação. |  |
| `pagina` | varchar | Página da publicação. |  |
| `coluna` | varchar | Coluna da página. |  |
| `fl_tem_texto` | boolean | A fonte informa que há o texto da publicação. |  |
| `dt_captura` | date | Data da captura do arquivo de origem. |  |
| `id_captura` | bigint | Captura do arquivo de origem (URL, data e hash em metadata.capturas). |  |

### marts.fct_pessoas_fusoes

| Coluna | Tipo | Descrição | Dado pessoal |
| --- | --- | --- | --- |
| `id_pessoa_absorvida` | bigint | Chave que deixou de existir. |  |
| `id_pessoa_sobrevivente` | bigint | Chave que a substituiu (dim_pessoas_cadastro). |  |
| `metodo` | varchar | Regra que ligou as duas chaves. |  |
| `dt_fusao` | timestamp | Momento da fusão. |  |

### marts.fct_pessoas_partidos

| Coluna | Tipo | Descrição | Dado pessoal |
| --- | --- | --- | --- |
| `fonte` | varchar | Fonte oficial do registro (camara, senado ou tse). |  |
| `base` | varchar | De onde sai o partido: historico_de_deputados (períodos do histórico da Câmara), inicio_da_legislatura (partido no início de cada legislatura, para deputados sem períodos no histórico), votos (partido do parlamentar em cada voto, só para quem não tem histórico) ou candidatura (partido pelo qual concorreu no TSE). |  |
| `id_pessoa_partido` | varchar | Identificador da linha: fonte e o registro de origem (Câmara: deputado e momento do primeiro registro; TSE: candidatura). |  |
| `id_pessoa` | bigint | Pessoa do projeto (dim_pessoas). |  |
| `id_partido` | integer | Partido (dim_partidos), achado pela sigla e pelo ano. Vazio para registro sem partido (S.Part.) e para sigla não curada; o teste de aviso mede as não curadas. |  |
| `partido_na_fonte` | varchar | Sigla do partido como a fonte informa. |  |
| `ano_referencia` | bigint | Ano do momento: o do primeiro registro da Câmara ou o da eleição da candidatura. |  |
| `dt_inicio` | date | Só na Câmara: data do primeiro registro com este partido. |  |
| `dt_ultimo_registro` | date | Só na Câmara: data do último registro com este partido; não é o fim da filiação. |  |
| `id_candidatura` | varchar | Só no TSE: candidatura pela qual a pessoa concorreu por este partido. |  |
| `fl_mais_recente` | boolean | Verdadeiro na linha mais recente da pessoa (maior ano de referência; na Câmara, o último registro). É o partido mais recente que as fontes mostram, não necessariamente o de hoje. |  |
| `id_captura` | bigint | Captura do arquivo de origem (URL, data e hash em metadata.capturas). |  |
| `dt_captura` | date | Data da captura do arquivo de origem. |  |

### marts.fct_proposicoes

| Coluna | Tipo | Descrição | Dado pessoal |
| --- | --- | --- | --- |
| `fonte` | varchar | Fonte oficial do registro (por exemplo, camara). |  |
| `id_proposicao` | varchar | Identificador da proposição na fonte. |  |
| `sigla` | varchar | Sigla do tipo da proposição, número e ano. |  |
| `ementa` | varchar | Ementa padronizada (caixa); igual à oficial quando já estava em caixa mista. CPF após o rótulo CPF é mascarado (***.nnn.nnn-**) pelo projeto; o original fica no landing. |  |
| `ementa_oficial` | varchar | Texto oficial da fonte, sem outra alteração além da máscara do CPF que vier após o rótulo CPF (***.nnn.nnn-**, feita pelo projeto); o original fica no landing. |  |
| `dt_apresentacao` | date | Data de apresentação. |  |
| `situacao` | varchar | Situação atual segundo a fonte. |  |
| `orgao_ultimo_status` | varchar | Órgão do último andamento. |  |
| `dt_ultimo_status` | date | Data do último andamento. |  |
| `fonte_url` | varchar | Endereço da proposição na fonte oficial. |  |
| `dt_captura` | date | Data da captura do arquivo de origem. |  |
| `id_captura` | bigint | Captura do arquivo de origem (URL, data e hash em metadata.capturas). |  |

### marts.fct_proposicoes_tramitacoes

| Coluna | Tipo | Descrição | Dado pessoal |
| --- | --- | --- | --- |
| `fonte` | varchar | Fonte oficial do registro. |  |
| `id_proposicao` | varchar | Proposição (fct_proposicoes, junto com a fonte). |  |
| `sequencia` | integer | Número do andamento dentro da proposição. |  |
| `dt_registro` | timestamp | Data e hora do andamento. |  |
| `orgao_sigla` | varchar | Órgão em que ocorreu. |  |
| `regime` | varchar | Regime de tramitação informado. |  |
| `descricao` | varchar | Descrição do tipo de andamento. |  |
| `situacao` | varchar | Situação da proposição após o andamento. |  |
| `despacho` | varchar | Texto do despacho, como a fonte informa. |  |
| `dt_captura` | date | Data da captura do lote de origem. |  |
| `id_captura` | bigint | Captura do arquivo de origem (URL, data e hash em metadata.capturas). |  |

### marts.fct_resultados

| Coluna | Tipo | Descrição | Dado pessoal |
| --- | --- | --- | --- |
| `fonte` | varchar | Fonte oficial do registro (tse). |  |
| `id_candidatura` | varchar | Candidatura (fct_candidaturas). |  |
| `turno` | integer | Turno da votação. |  |
| `situacao_candidatura` | varchar | Situação da candidatura no turno, como o arquivo de candidaturas informa. |  |
| `resultado` | varchar | Resultado do turno como o arquivo de candidaturas do TSE informa; vazio quando não informa. |  |
| `resultado_votacao` | varchar | Resultado do turno como o arquivo de votação do TSE informa; vazio quando não informa. |  |
| `qtd_votos_validos` | bigint | Votos válidos do candidato no turno, somados de todos os municípios e zonas; vazio se a votação não foi carregada. |  |
| `qtd_votos_nominais` | bigint | Votos nominais do candidato no turno, somados de todos os municípios e zonas. |  |
| `percentual_votos_validos` | decimal(5,2) | Percentual dos votos válidos do candidato sobre os votos válidos de todos os candidatos da mesma disputa e turno, sem votos de legenda; vazio sem votos carregados. |  |
| `fl_mais_votado_no_turno` | boolean | DERIVADO dos votos, não é resultado do TSE: só para presidente, governador e prefeito, verdadeiro se teve mais votos válidos no turno; vazio sem votos carregados ou em cargo de várias vagas. |  |
| `id_captura` | bigint | Captura do arquivo de candidaturas de origem (URL, data e hash em metadata.capturas). |  |
| `dt_captura` | date | Data da captura do arquivo de origem. |  |

### marts.fct_vetos

| Coluna | Tipo | Descrição | Dado pessoal |
| --- | --- | --- | --- |
| `fonte` | varchar | Fonte oficial do registro. |  |
| `id_veto` | bigint | Código do veto no Senado. |  |
| `id_materia_veto` | bigint | Código da matéria do veto (a que tramita no Congresso). |  |
| `numero` | integer | Número do veto no ano. |  |
| `ano` | integer | Ano do veto. |  |
| `id_materia_vetada` | bigint | Código da matéria vetada (o projeto aprovado). |  |
| `materia_vetada_sigla` | varchar | Sigla da matéria vetada (PL, PLN, PLP...). |  |
| `materia_vetada_numero` | varchar | Número da matéria vetada. |  |
| `materia_vetada_ano` | integer | Ano da matéria vetada. |  |
| `materia_vetada_ementa` | varchar | Ementa da matéria vetada, com caixa padronizada. |  |
| `id_norma` | bigint | Norma gerada pela matéria (fct_normas); vazia quando não houve. |  |
| `norma_nome` | varchar | Nome da norma gerada. |  |
| `mensagem_numero` | integer | Número da mensagem presidencial do veto. |  |
| `mensagem_ano` | integer | Ano da mensagem presidencial. |  |
| `mensagem_url` | varchar | Mensagem presidencial no Planalto, como a fonte informa. |  |
| `fl_veto_total` | boolean | Veto total (verdadeiro) ou parcial (falso). |  |
| `assunto` | varchar | Assunto do veto, como a fonte informa. |  |
| `dt_recebimento` | date | Data em que o Congresso recebeu o veto. |  |
| `dt_publicacao` | date | Data de publicação do veto. |  |
| `dt_sobrestamento` | date | Data em que o veto passou a trancar a pauta. |  |
| `fl_sobrestando_pauta` | boolean | O veto tranca a pauta hoje. |  |
| `quantidade_dispositivos` | integer | Quantos dispositivos foram vetados. |  |
| `fl_em_tramitacao` | boolean | O veto ainda tramita. |  |
| `fonte_url` | varchar | Página oficial da matéria do veto no Senado. |  |
| `dt_captura` | date | Data da captura do arquivo de origem. |  |
| `id_captura` | bigint | Captura do arquivo de origem (URL, data e hash em metadata.capturas). |  |

### marts.fct_vetos_dispositivos

| Coluna | Tipo | Descrição | Dado pessoal |
| --- | --- | --- | --- |
| `fonte` | varchar | Fonte oficial do registro. |  |
| `id_dispositivo` | bigint | Código do dispositivo vetado no Senado; vazio no veto total, que a fonte não codifica. |  |
| `id_materia_veto` | bigint | Código da matéria do veto (fct_vetos). |  |
| `id_veto` | bigint | Veto a que o dispositivo pertence (fct_vetos). |  |
| `identificador` | varchar | Identificador do dispositivo no veto (veto.ano.item); único dentro do veto. |  |
| `descricao` | varchar | Onde o dispositivo está na norma (por exemplo, art. 7º, § 4º, inciso II). |  |
| `texto_vetado` | varchar | Texto que foi vetado, como a fonte publica. |  |
| `razao_veto` | varchar | Razão do veto escrita pela Presidência, como a fonte publica. |  |
| `situacao` | varchar | Situação como a fonte informa: Mantido (o veto vale), Rejeitado (o Congresso derrubou o veto), Prejudicado ou Não Apreciado. |  |
| `fl_possui_votos` | boolean | Há voto nominal registrado para o dispositivo. |  |
| `tipo_votacao` | varchar | Forma da votação (painel ou cédula); vazia quando não foi apreciado. |  |
| `dt_sessao` | date | Data da sessão do Congresso que apreciou o dispositivo. |  |
| `dt_captura` | date | Data da captura do arquivo de origem. |  |
| `id_captura` | bigint | Captura do arquivo de origem (URL, data e hash em metadata.capturas). |  |

### marts.fct_vetos_votos

| Coluna | Tipo | Descrição | Dado pessoal |
| --- | --- | --- | --- |
| `fonte` | varchar | Fonte oficial do registro. |  |
| `id_dispositivo` | bigint | Dispositivo votado (fct_vetos_dispositivos). |  |
| `casa` | varchar | Câmara ou Senado. |  |
| `nome_parlamentar` | varchar | Nome do parlamentar como a fonte informa, com caixa padronizada. |  |
| `partido` | varchar | Partido na sessão, como a fonte informa. |  |
| `uf` | varchar | UF do parlamentar. |  |
| `voto` | varchar | Voto como a fonte informa (Sim, Não, Branco, Abstenção...). |  |
| `sessao` | varchar | Sessão do Congresso, como a fonte informa. |  |
| `dt_captura` | date | Data da captura do arquivo de origem. |  |
| `id_captura` | bigint | Captura do arquivo de origem (URL, data e hash em metadata.capturas). |  |

### marts.fct_votacoes

| Coluna | Tipo | Descrição | Dado pessoal |
| --- | --- | --- | --- |
| `fonte` | varchar | Fonte oficial do registro. |  |
| `id_votacao` | varchar | Identificador da votação na fonte. |  |
| `dt_votacao` | date | Data da votação. |  |
| `orgao_sigla` | varchar | Sigla do órgão em que ocorreu. |  |
| `descricao` | varchar | Descrição oficial da votação, com caixa padronizada. CPF após o rótulo CPF é mascarado (***.nnn.nnn-**) pelo projeto; o original fica no landing. |  |
| `aprovada` | integer | 1 se a fonte registra aprovação; 0 se não; vazio se não informa. |  |
| `votos_sim` | integer | Total de votos Sim informado pela fonte. |  |
| `votos_nao` | integer | Total de votos Não informado pela fonte. |  |
| `votos_outros` | integer | Total de outros votos informado pela fonte. |  |
| `proposicoes` | varchar | Proposições ligadas à votação, separadas por ponto e vírgula. |  |
| `fl_votacao_secreta` | boolean | Verdadeiro se a votação foi secreta; vazio onde a fonte não informa (Câmara). |  |
| `dt_captura` | date | Data da captura do arquivo de origem. |  |
| `id_captura` | bigint | Captura do arquivo de origem (URL, data e hash em metadata.capturas). |  |

### marts.fct_votos

| Coluna | Tipo | Descrição | Dado pessoal |
| --- | --- | --- | --- |
| `fonte` | varchar | Fonte oficial do voto (camara ou senado). |  |
| `id_votacao` | varchar | Identificador da votação na fonte. |  |
| `id_pessoa` | bigint | Pessoa do projeto (dim_pessoas). |  |
| `voto` | varchar | Voto registrado, como a fonte informa (sim, não, abstenção, obstrução...). |  |
| `dt_voto` | timestamp | Data e hora do voto, como a fonte informa. |  |
| `id_partido` | integer | Partido na data do voto (dim_partidos). Vazio para voto sem partido e para sigla não curada. |  |
| `partido_na_fonte` | varchar | Sigla do partido como a fonte informa no voto. |  |
| `uf` | varchar | UF do parlamentar no voto, como a fonte informa. |  |
| `id_captura` | bigint | Captura do arquivo de origem (URL, data e hash em metadata.capturas). |  |
| `dt_captura` | date | Data da captura do arquivo de origem. |  |
