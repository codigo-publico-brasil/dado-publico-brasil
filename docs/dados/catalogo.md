# Catálogo de dados

Gerado do projeto dbt (`plataforma catalog`). Não edite à mão: edite a descrição e o `meta` do modelo ou da fonte e gere de novo.

## raw_federal_camara

| Tabela | O que é | Sensibilidade | Grain |
| --- | --- | --- | --- |
| `deputados` | Cadastro de deputados (sem documentos pessoais). | publico-agente-publico |  |
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
| `senadores_detalhe` | Detalhe de cada senador, buscado por item na API (`_item` é o código do senador): nascimento, naturalidade e foto, só dos já buscados. | publico-agente-publico |  |
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
| `emendas` | Emendas parlamentares por localidade, função, programa e ação, com os valores empenhado, liquidado e pago. | publico |  |
| `emendas_convenios` | Convênios firmados com recursos de emendas parlamentares. | publico |  |
| `emendas_favorecidos` | Quem recebeu o dinheiro das emendas, só pessoa jurídica e unidade gestora. | publico |  |

## raw_federal_tse

| Tabela | O que é | Sensibilidade | Grain |
| --- | --- | --- | --- |
| `bens` | Bens declarados pelos candidatos de todos os cargos nas eleições gerais de 2006 em diante, uma linha por bem. | publico-agente-publico |  |
| `candidaturas` | Candidaturas a deputado federal e senador (e suplentes) nas eleições gerais, uma linha por candidatura. | publico-agente-publico |  |
| `votacao` | Votos de cada candidato (todos os cargos) por município e zona nas eleições gerais já carregadas, como o TSE publica. | publico-agente-publico |  |

## staging

| Tabela | O que é | Sensibilidade | Grain |
| --- | --- | --- | --- |
| `stg_camara__deputados` | Deputados, uma linha por deputado, com nomes padronizados e tipos corretos. | publico-agente-publico |  |
| `stg_camara__deputados_ocupacoes` | Ocupações anteriores declaradas por deputado. | publico-agente-publico |  |
| `stg_camara__deputados_profissoes` | Profissões declaradas por deputado (linhas sem título descartadas pela padronização). | publico-agente-publico |  |
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
| `stg_identity__pessoa_fusoes` | Chaves de pessoa absorvidas por outra quando se mostraram a mesma pessoa, uma linha por chave absorvida. | publico-agente-publico |  |
| `stg_identity__pessoa_identificadores` | Identificadores de cada pessoa em cada fonte. | publico-agente-publico |  |
| `stg_identity__pessoas` | Pessoas do projeto (chave própria). | publico-agente-publico |  |
| `stg_metadata__captures` | Capturas dos arquivos da fonte (um arquivo, uma linha). `source_file_id` liga as linhas do raw ao arquivo. | publico-agente-publico |  |
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
| `stg_transparencia__emendas` | Emendas parlamentares, uma linha por emenda, localidade, função, programa e ação. | publico-agente-publico |  |
| `stg_transparencia__emendas_convenios` | Convênios firmados com recursos de emendas parlamentares. | publico-agente-publico |  |
| `stg_transparencia__emendas_favorecidos` | Quem recebeu o dinheiro de cada emenda (só pessoa jurídica e unidade gestora), por mês. | publico-agente-publico |  |
| `stg_tse__bens` | Bens declarados pelos candidatos de todos os cargos, uma linha por bem. | publico-agente-publico |  |
| `stg_tse__candidaturas` | Candidaturas ao Congresso (deputado federal e senador, com suplentes) nas eleições gerais, uma linha por candidatura e turno. | publico-agente-publico |  |
| `stg_tse__votacao` | Votos de cada candidato (todos os cargos) por município e zona, como o TSE publica. | publico-agente-publico |  |

## intermediate

| Tabela | O que é | Sensibilidade | Grain |
| --- | --- | --- | --- |
| `int_autorias_ligadas_a_pessoas` | Autorias com a pessoa do projeto; autor que não é deputado fica sem pessoa. | publico-agente-publico |  |
| `int_deputados_fotos_das_frentes` | Uma foto por deputado, a da legislatura mais recente nos arquivos de frentes. | publico-agente-publico |  |
| `int_deputados_ids_unidos` | Todo deputado informado pela Câmara (cadastro mais votos). | publico-agente-publico |  |
| `int_deputados_nos_votos_agregados` | Um registro por deputado visto nos votos, com nome e foto mais recentes. | publico-agente-publico |  |
| `int_frentes_membros_ligados_a_pessoas` | Participação em frentes ligada à pessoa do projeto. | publico-agente-publico |  |
| `int_materias_do_senado_unicas` | Uma linha por matéria votada no Senado, com os dados da votação mais recente. | publico-agente-publico |  |
| `int_orgaos_membros_ligados_a_pessoas` | Participação em órgãos ligada à pessoa do projeto. | publico-agente-publico |  |
| `int_pessoas_atividade_agregada` | Uma linha por pessoa, com votos, propostas e legislaturas. | publico-agente-publico |  |
| `int_pessoas_do_senado_unidas_ao_cadastro` | Pessoa do projeto unida ao cadastro do Senado. | publico-agente-publico |  |
| `int_pessoas_ids_vistos` | Todo identificador de pessoa informado pelas fontes. Entrada do código de identidade. | publico-agente-publico |  |
| `int_pessoas_para_vinculo` | Pessoas das duas casas com nome civil (como chave) e nascimento, para ligar entre fontes. | publico-agente-publico |  |
| `int_pessoas_profissoes_agregadas` | Uma linha por pessoa, com as profissões declaradas. | publico-agente-publico |  |
| `int_pessoas_unidas_ao_cadastro` | Pessoa do projeto unida ao cadastro e aos dados vistos nos votos. | publico-agente-publico |  |
| `int_senadores_unidos` | Todo senador informado pelo Senado (cadastro mais votos). | publico-agente-publico |  |
| `int_siglas_em_ementas_extraidas` | Siglas escritas em maiúsculas dentro de ementas de caixa mista. | publico-agente-publico |  |
| `int_vinculos_propostos` | Vínculos propostos entre fontes pela regra de nome civil e nascimento iguais e únicos: Câmara com Senado (mesma pessoa) e candidatura do TSE com a pessoa. Entrada da identidade. | publico-agente-publico |  |
| `int_votacoes_proposicoes_unidas` | Proposições de cada votação, com o papel (afetada ou objeto). | publico-agente-publico |  |
| `int_votos_ligados_a_pessoas` | Votos com a pessoa do projeto (chave própria). | publico-agente-publico |  |

## marts

| Tabela | O que é | Sensibilidade | Grain |
| --- | --- | --- | --- |
| `autorias` | Proposições de que cada pessoa é autora ou apoiadora, com a posição na assinatura e o total de autores. Uma linha por pessoa e proposição. | publico-agente-publico | pessoa e proposição |
| `bens_de_candidatos` | Bens declarados à Justiça Eleitoral por candidatos que já são pessoa do projeto, de 2006 em diante, como o TSE publica (valor declarado, sem correção). Uma linha por bem. | publico-agente-publico | candidatura e bem |
| `candidaturas` | Candidaturas ao Congresso (deputado federal e senador, com suplentes) de quem já é pessoa do projeto, com partido, situação e resultado. Uma linha por candidatura e turno. | publico-agente-publico | pessoa |
| `constituicao_alteracoes` | Cada indicação de emenda que o texto da Constituição traz entre parênteses, por dispositivo (por exemplo, Redação dada pela Emenda Constitucional nº 45, de 2004). Uma linha por dispositivo e emenda citada. | publico | dispositivo e emenda citada |
| `constituicao_dispositivos` | A Constituição de 1988 e o ADCT dispositivo a dispositivo, como a Câmara publica (texto atualizado até a emenda indicada). O tipo e o contexto saem da posição e do começo de cada linha; o texto não é reescrito. Uma linha por parágrafo do arquivo. | publico | parágrafo do arquivo |
| `dispositivos_vetados` | Cada dispositivo vetado, com o texto vetado, a razão do veto escrita pela Presidência e o que o Congresso decidiu (situação como a fonte informa). Só dos vetos já buscados. Uma linha por dispositivo. | publico | dispositivo vetado |
| `emendas` | Emendas parlamentares ao orçamento federal como o Portal da Transparência publica, com valores empenhado, liquidado e pago. O autor vem pelo nome e pelo código orçamentário (não é o código do parlamentar), por isso não ligado a pessoas. Uma linha por emenda, localidade, função, programa e ação. | publico | emenda |
| `emendas_convenios` | Convênios firmados com recursos de emendas parlamentares, como o Portal da Transparência publica, com convenente, objeto e valor. Uma linha por convênio e emenda. | publico | convênio e emenda |
| `emendas_favorecidos` | Quem recebeu o dinheiro de cada emenda parlamentar, por mês, como o Portal da Transparência publica. Só pessoa jurídica e unidade gestora, a pessoa física, cidadão comum, nunca entra. Uma linha por emenda, favorecido e mês. | publico | emenda |
| `exercicios` | Exercício oficial no cargo como o Senado informa (titular e suplentes), com início, fim e causa de afastamento. Só o Senado; a Câmara não publica. Uma linha por pessoa, mandato e exercício. | publico-agente-publico | pessoa |
| `frentes` | Frentes parlamentares, com legislatura de criação e coordenador. Uma linha por frente. | publico | frente parlamentar |
| `fusoes_de_pessoas` | Chaves de pessoa absorvidas por outra quando se mostraram a mesma pessoa (por exemplo, deputado que virou senador). Uma linha por chave absorvida. | publico-agente-publico | chave absorvida |
| `legislaturas` | Legislaturas da Câmara, com datas oficiais de início e fim. Uma linha por legislatura. | publico | legislatura |
| `linhagem_de_partidos` | Mudanças de nome, fusões e incorporações de partidos, conforme o TSE, com a página oficial de cada evento. Curada à mão; só o que foi conferido. Uma linha por partido de origem e evento. | publico | partido de origem e evento |
| `mandatos` | Mandatos por legislatura, a partir de votos observados (início e fim oficiais vazios). Uma linha por pessoa e legislatura. | publico-agente-publico | pessoa e legislatura |
| `membros_de_frentes` | Participação de pessoas em frentes parlamentares, com o título e a legislatura. Uma linha por pessoa, frente, legislatura e título. | publico-agente-publico | pessoa |
| `membros_de_orgaos` | Participação de pessoas em órgãos da Câmara, com cargo e período. Uma linha por pessoa, órgão, cargo e período informado. | publico-agente-publico | pessoa |
| `normas` | Catálogo das normas federais (leis, decretos, medidas provisórias, emendas...) desde 1808, só metadados; o texto integral não vem desta fonte. Uma linha por norma. | publico | norma |
| `normas_geradas` | Norma jurídica que resultou de uma matéria, com número, datas e veículo de publicação. Só o Senado informa por enquanto. Uma linha por matéria. | publico | matéria |
| `normas_publicacoes` | Onde cada norma foi publicada no Diário Oficial (a original e, por exemplo, a do veto), com página e coluna. Só das normas detalhadas. Uma linha por norma e publicação. | publico | norma e publicação |
| `normas_relacoes` | Ligações de cada norma com atos posteriores, como o Senado declara (alteração, regulamentação, veto, declaração de constitucionalidade). Só das normas detalhadas (leis, leis complementares, emendas, medidas provisórias e a Constituição). Uma linha por norma, ato posterior e tipo de relação. | publico | norma |
| `ocupacoes` | Ocupações anteriores declaradas. Uma linha por pessoa e ocupação. | publico-agente-publico | pessoa e ocupação |
| `orgaos` | Órgãos da Câmara (comissões, plenário, mesa diretora, conselhos), com tipo e situação. Uma linha por órgão. | publico | órgão |
| `partidos` | Partidos com sigla e nome oficiais. Uma linha por partido. | publico | partido |
| `pessoas` | Pessoas (agentes públicos) com perfil, contagens e último partido. Uma linha por pessoa. | publico-agente-publico | pessoa |
| `proposicoes` | Proposições com ementa padronizada, ementa oficial, situação atual e URL da fonte. Uma linha por proposição. | publico | proposição |
| `tramitacoes` | Andamentos das proposições que podem virar norma (só as já buscadas), na ordem em que ocorreram. Uma linha por proposição e sequência. | publico | proposição e sequência |
| `vetos` | Vetos presidenciais apreciados pelo Congresso, de 1994 em diante (antes disso a fonte não informa), com a matéria vetada, a norma gerada e as datas. Uma linha por veto. | publico | veto |
| `votacoes` | Votações com resultado oficial, totais e proposições. Uma linha por votação. | publico | votação |
| `votos` | Voto de cada pessoa em cada votação nominal, com partido e UF na data. Uma linha por pessoa e votação. | publico-agente-publico | pessoa e votação |
| `votos_de_candidatos` | Votos de cada candidatura de quem já é pessoa do projeto, somados dos municípios e zonas, nas eleições gerais já carregadas. Uma linha por candidatura e turno. | publico-agente-publico | candidatura e turno |
| `votos_em_vetos` | Voto de deputados e senadores em cada dispositivo vetado votado, como a fonte entrega (nome, partido e UF, sem o código do parlamentar), por isso não ligado a pessoas. Só dos dispositivos já buscados. Uma linha por dispositivo e voto. | publico-agente-publico | dispositivo e voto |

## identity

| Tabela | O que é | Sensibilidade | Grain |
| --- | --- | --- | --- |
| `pessoa` | Pessoa do projeto, com chave própria, independente da fonte. | publico-agente-publico |  |
| `pessoa_fusao` | Chaves de pessoa absorvidas por outra quando se mostraram a mesma pessoa. | publico-agente-publico |  |
| `pessoa_identificador` | Ponte entre a chave da pessoa e o identificador em cada fonte, com método e confirmação. | publico-agente-publico |  |

## metadata

| Tabela | O que é | Sensibilidade | Grain |
| --- | --- | --- | --- |
| `captures` | Cada arquivo recebido da fonte, com URL, hash, caminho no landing e datas. | controle |  |
| `dbt_results` | Resultado de cada modelo e teste do dbt na última execução de cada comando. | controle |  |
| `runs` | Cada execução de etapa do pipeline, com início, fim, versão do código e resultado. | controle |  |

## Dicionário de colunas dos marts

### marts.autorias

| Coluna | Tipo | Descrição |
| --- | --- | --- |
| `id_pessoa` | bigint | Chave da pessoa (marts.pessoas). |
| `fonte` | varchar | Fonte oficial do registro. |
| `proposicao_id` | varchar | Identificador da proposição na fonte. |
| `ordem_assinatura` | integer | Posição na assinatura. |
| `qtd_autores` | bigint | Total de autores da proposição. |
| `proponente` | integer | 1 quando consta como proponente; 0 caso contrário. |
| `proposicao_fonte_url` | varchar | Endereço da proposição na fonte oficial. |

### marts.bens_de_candidatos

| Coluna | Tipo | Descrição |
| --- | --- | --- |
| `fonte` | varchar | Fonte oficial do registro. |
| `id_pessoa` | bigint | Chave da pessoa (marts.pessoas). |
| `candidatura_id` | varchar | Candidatura (marts.candidaturas): ano da eleição e sequencial do candidato. |
| `ano_eleicao` | integer | Ano da eleição. |
| `ordem` | integer | Número do bem na declaração do candidato. |
| `tipo` | varchar | Tipo do bem (imóvel, veículo, aplicação financeira etc.). |
| `descricao` | varchar | Descrição do bem, como o candidato declarou. |
| `valor` | decimal(18,2) | Valor declarado em reais, sem correção. |
| `atualizado_em` | date | Data da última atualização do bem na declaração. |
| `capturado_em` | date | Data da captura do arquivo de origem. |

### marts.candidaturas

| Coluna | Tipo | Descrição |
| --- | --- | --- |
| `fonte` | varchar | Fonte oficial do registro (tse). |
| `id_pessoa` | bigint | Chave da pessoa (marts.pessoas), ligada por nome civil e data de nascimento iguais e únicos. |
| `candidatura_id` | varchar | Identificador da candidatura na fonte: ano da eleição e sequencial do candidato. |
| `ano_eleicao` | integer | Ano da eleição. |
| `turno` | integer | Turno da votação. |
| `uf` | varchar | UF da candidatura (BR para cargos nacionais). |
| `cargo` | varchar | Cargo disputado. |
| `numero` | varchar | Número do candidato na urna. |
| `nome_urna` | varchar | Nome de urna, com caixa padronizada. |
| `partido` | varchar | Sigla do partido na eleição. |
| `partido_nome` | varchar | Nome do partido na eleição. |
| `situacao_candidatura` | varchar | Situação da candidatura segundo a fonte (por exemplo, deferido). |
| `resultado` | varchar | Resultado da votação segundo a fonte (eleito por QP, eleito por média, suplente, não eleito); vazio se não informado. |
| `capturado_em` | date | Data da captura do arquivo de origem. |

### marts.constituicao_alteracoes

| Coluna | Tipo | Descrição |
| --- | --- | --- |
| `parte` | varchar | Constituição (parte permanente) ou ADCT. |
| `ordem` | integer | Posição do parágrafo no arquivo (marts.constituicao_dispositivos). |
| `identificador` | varchar | Caminho do dispositivo (marts.constituicao_dispositivos). |
| `tipo_alteracao` | varchar | Tirado das palavras da nota: redação dada, incluído, revogado, suprimido, renumerado, vide (só referência) ou outra. |
| `emenda_tipo` | varchar | Emenda Constitucional ou Emenda Constitucional de Revisão. |
| `emenda_numero` | integer | Número da emenda citada na nota. |
| `emenda_ano` | integer | Ano da emenda; só quando a nota cita uma emenda. |
| `nota` | varchar | A nota como o texto publica, sem os parênteses. |

### marts.constituicao_dispositivos

| Coluna | Tipo | Descrição |
| --- | --- | --- |
| `parte` | varchar | Constituição (parte permanente) ou ADCT. |
| `ordem` | integer | Posição do parágrafo no arquivo, a partir de 1. |
| `tipo` | varchar | Cabeçalho do arquivo, preâmbulo, título, capítulo, seção, subseção, artigo, parágrafo, inciso, alínea, item, texto ou assinaturas. |
| `identificador` | varchar | Caminho do dispositivo (Art. 5º, § 1º, I, a)); vazio em títulos, capítulos e linhas sem artigo. |
| `artigo` | varchar | Número do artigo a que a linha pertence. |
| `paragrafo` | varchar | Número do parágrafo (ou único) a que a linha pertence. |
| `inciso` | varchar | Inciso (algarismo romano) a que a linha pertence. |
| `alinea` | varchar | Alínea (letra) a que a linha pertence. |
| `titulo` | varchar | Título (cabeçalho) em que a linha está. |
| `capitulo` | varchar | Capítulo (cabeçalho) em que a linha está. |
| `secao` | varchar | Seção (cabeçalho) em que a linha está. |
| `texto` | varchar | A linha inteira como a Câmara publica, com a indicação da emenda que a alterou. |
| `atualizada_ate_emenda` | integer | Número da emenda constitucional até a qual o arquivo está atualizado. |
| `fonte_url` | varchar | Página oficial da Câmara com o texto atualizado. |
| `capturado_em` | date | Data da captura do arquivo de origem. |

### marts.dispositivos_vetados

| Coluna | Tipo | Descrição |
| --- | --- | --- |
| `fonte` | varchar | Fonte oficial do registro. |
| `dispositivo_id` | bigint | Código do dispositivo vetado no Senado. |
| `materia_veto_id` | bigint | Código da matéria do veto (marts.vetos). |
| `veto_id` | bigint | Veto a que o dispositivo pertence (marts.vetos). |
| `identificador` | varchar | Identificador do dispositivo no veto (veto.ano.item). |
| `descricao` | varchar | Onde o dispositivo está na norma (por exemplo, art. 7º, § 4º, inciso II). |
| `texto_vetado` | varchar | Texto que foi vetado, como a fonte publica. |
| `razao_veto` | varchar | Razão do veto escrita pela Presidência, como a fonte publica. |
| `situacao` | varchar | Situação como a fonte informa: Mantido (o veto vale), Rejeitado (o Congresso derrubou o veto), Prejudicado ou Não Apreciado. |
| `possui_votos` | boolean | Há voto nominal registrado para o dispositivo. |
| `tipo_votacao` | varchar | Forma da votação (painel ou cédula); vazia quando não foi apreciado. |
| `sessao_em` | date | Data da sessão do Congresso que apreciou o dispositivo. |
| `capturado_em` | date | Data da captura do arquivo de origem. |

### marts.emendas

| Coluna | Tipo | Descrição |
| --- | --- | --- |
| `fonte` | varchar | Fonte oficial do registro. |
| `emenda_codigo` | varchar | Código da emenda; vazio em registros antigos sem código. |
| `ano` | integer | Ano da emenda. |
| `tipo` | varchar | Tipo da emenda (individual, de bancada, de comissão, de relator). |
| `autor_codigo` | varchar | Código orçamentário do autor; vazio quando a fonte não informa. |
| `autor_nome` | varchar | Nome do autor (parlamentar, bancada, comissão ou relator-geral), com caixa padronizada. |
| `numero` | varchar | Número da emenda. |
| `localidade` | varchar | Localidade de aplicação do recurso, como a fonte informa. |
| `municipio_ibge` | integer | Código IBGE do município. |
| `municipio` | varchar | Município de aplicação. |
| `uf` | varchar | UF de aplicação, como a fonte informa. |
| `regiao` | varchar | Região. |
| `funcao` | varchar | Função orçamentária. |
| `subfuncao` | varchar | Subfunção orçamentária. |
| `programa_codigo` | varchar | Código do programa. |
| `programa` | varchar | Programa. |
| `acao_codigo` | varchar | Código da ação. |
| `acao` | varchar | Ação orçamentária. |
| `plano_orcamentario` | varchar | Plano orçamentário. |
| `valor_empenhado` | decimal(18,2) | Valor empenhado em reais. |
| `valor_liquidado` | decimal(18,2) | Valor liquidado em reais. |
| `valor_pago` | decimal(18,2) | Valor pago em reais. |
| `valor_restos_a_pagar_inscritos` | decimal(18,2) | Restos a pagar inscritos em reais. |
| `valor_restos_a_pagar_cancelados` | decimal(18,2) | Restos a pagar cancelados em reais. |
| `valor_restos_a_pagar_pagos` | decimal(18,2) | Restos a pagar pagos em reais. |
| `capturado_em` | date | Data da captura do arquivo de origem. |

### marts.emendas_convenios

| Coluna | Tipo | Descrição |
| --- | --- | --- |
| `fonte` | varchar | Fonte oficial do registro. |
| `emenda_codigo` | varchar | Código da emenda (marts.emendas). |
| `funcao` | varchar | Função orçamentária. |
| `subfuncao` | varchar | Subfunção orçamentária. |
| `localidade` | varchar | Localidade do gasto, como a fonte informa. |
| `tipo` | varchar | Tipo da emenda. |
| `publicado_em` | date | Data de publicação do convênio. |
| `convenente` | varchar | Quem firmou o convênio. |
| `objeto` | varchar | Objeto do convênio. |
| `convenio_numero` | varchar | Número do convênio. |
| `valor` | decimal(18,2) | Valor do convênio em reais. |
| `capturado_em` | date | Data da captura do arquivo de origem. |

### marts.emendas_favorecidos

| Coluna | Tipo | Descrição |
| --- | --- | --- |
| `fonte` | varchar | Fonte oficial do registro. |
| `emenda_codigo` | varchar | Código da emenda (marts.emendas). |
| `autor_codigo` | varchar | Código orçamentário do autor da emenda. |
| `autor_nome` | varchar | Nome do autor da emenda, com caixa padronizada. |
| `numero` | varchar | Número da emenda. |
| `tipo` | varchar | Tipo da emenda. |
| `ano` | integer | Ano do pagamento. |
| `mes` | integer | Mês do pagamento. |
| `favorecido_codigo` | varchar | CNPJ ou código da unidade gestora do favorecido. |
| `favorecido` | varchar | Nome do favorecido. |
| `natureza_juridica` | varchar | Natureza jurídica do favorecido. |
| `tipo_favorecido` | varchar | Pessoa jurídica ou unidade gestora. |
| `uf` | varchar | UF do favorecido. |
| `municipio` | varchar | Município do favorecido. |
| `valor` | decimal(18,2) | Valor recebido em reais. |
| `capturado_em` | date | Data da captura do arquivo de origem. |

### marts.exercicios

| Coluna | Tipo | Descrição |
| --- | --- | --- |
| `fonte` | varchar | Fonte oficial do registro. |
| `id_pessoa` | bigint | Chave da pessoa (marts.pessoas). |
| `mandato_id` | varchar | Código do mandato no Senado (titular e suplentes compartilham o mesmo). |
| `exercicio_id` | varchar | Código do período de exercício no Senado. |
| `participacao` | varchar | Titular, 1º suplente ou 2º suplente. |
| `uf` | varchar | UF que o mandato representa. |
| `mandato_inicio` | date | Início do mandato (da primeira legislatura que ele cobre). |
| `mandato_fim` | date | Fim do mandato (da última legislatura que ele cobre). |
| `inicio` | date | Início deste período de exercício. |
| `fim` | date | Fim deste período; vazio enquanto está em exercício. |
| `causa_afastamento_sigla` | varchar | Sigla da causa do fim do período (licença, renúncia, fim do mandato); vazia se não informada. |
| `causa_afastamento` | varchar | Descrição da causa do fim do período. |

### marts.frentes

| Coluna | Tipo | Descrição |
| --- | --- | --- |
| `fonte` | varchar | Fonte oficial do registro. |
| `frente_id` | bigint | Identificador da frente na fonte. |
| `titulo` | varchar | Título da frente. |
| `criada_em` | date | Data de criação. |
| `legislatura_id` | integer | Legislatura em que foi criada. |
| `situacao` | varchar | Situação informada pela fonte. |
| `id_pessoa_coordenador` | bigint | Pessoa coordenadora (marts.pessoas); vazia se a fonte não informa ou não é deputado. |

### marts.fusoes_de_pessoas

| Coluna | Tipo | Descrição |
| --- | --- | --- |
| `id_pessoa_absorvida` | bigint | Chave que deixou de existir. |
| `id_pessoa_sobrevivente` | bigint | Chave que a substituiu (marts.pessoas). |
| `metodo` | varchar | Regra que ligou as duas chaves. |
| `fundida_em` | timestamp | Momento da fusão. |

### marts.legislaturas

| Coluna | Tipo | Descrição |
| --- | --- | --- |
| `fonte` | varchar | Fonte oficial do registro. |
| `legislatura_id` | integer | Número da legislatura. |
| `inicio` | date | Início oficial da legislatura. |
| `fim` | date | Fim oficial da legislatura. |
| `ano_eleicao` | integer | Ano da eleição que a formou. |

### marts.linhagem_de_partidos

| Coluna | Tipo | Descrição |
| --- | --- | --- |
| `sigla_anterior` | varchar | Sigla do partido antes do evento, como aparece nos votos. |
| `sigla_posterior` | varchar | Sigla depois do evento (a do partido resultante, em fusão e incorporação). |
| `tipo` | varchar | Mudança de nome, fusão ou incorporação. |
| `aprovado_em` | date | Data da aprovação pelo TSE; vazia quando só o mês é conhecido. |
| `ano` | integer | Ano do evento. |
| `fonte_url` | varchar | Página oficial do TSE que registra o evento. |
| `observacao` | varchar | Divergência de data, resolução ou ressalva da fonte. |

### marts.mandatos

| Coluna | Tipo | Descrição |
| --- | --- | --- |
| `fonte` | varchar | \"Fonte oficial do registro.\" |
| `id_pessoa` | bigint | Chave da pessoa (marts.pessoas). |
| `cargo` | varchar | Cargo exercido. |
| `casa` | varchar | Casa legislativa. |
| `legislatura_id` | integer | Número da legislatura. |
| `uf` | varchar | UF de eleição ou representação nos votos da legislatura. |
| `inicio` | date | Início oficial do mandato; vazio quando a fonte não informa. |
| `fim` | date | Fim oficial do mandato; vazio quando a fonte não informa. |
| `primeiro_voto_observado_em` | timestamp | Primeiro voto registrado na legislatura. |
| `ultimo_voto_observado_em` | timestamp | Último voto registrado na legislatura. |
| `base` | varchar | Origem do período: votos observados, não ato oficial. |
| `legislatura_inicio` | date | Início oficial da legislatura (não do mandato da pessoa). |
| `legislatura_fim` | date | Fim oficial da legislatura (não do mandato da pessoa). |

### marts.membros_de_frentes

| Coluna | Tipo | Descrição |
| --- | --- | --- |
| `fonte` | varchar | Fonte oficial do registro. |
| `frente_id` | bigint | Frente (marts.frentes). |
| `id_pessoa` | bigint | Chave da pessoa (marts.pessoas). |
| `titulo` | varchar | Título na frente (coordenador, membro etc.). |
| `legislatura_id` | integer | Legislatura do registro. |
| `inicio` | date | Início da participação, quando a fonte informa. |
| `fim` | date | Fim da participação, quando a fonte informa. |

### marts.membros_de_orgaos

| Coluna | Tipo | Descrição |
| --- | --- | --- |
| `fonte` | varchar | Fonte oficial do registro. |
| `orgao_id` | bigint | Órgão (marts.orgaos). Parte dos órgãos citados (Congresso, comissões especiais) não consta da lista de órgãos da fonte; o teste de relação mede essa lacuna. |
| `orgao_sigla` | varchar | Sigla do órgão como informada na própria linha de composição. |
| `id_pessoa` | bigint | Chave da pessoa (marts.pessoas). |
| `cargo` | varchar | Cargo no órgão (titular, suplente, presidente etc.). |
| `partido` | varchar | Partido informado no registro. |
| `uf` | varchar | UF informada no registro. |
| `inicio` | date | Início da participação. |
| `fim` | date | Fim da participação; vazio se a fonte não informa. |

### marts.normas

| Coluna | Tipo | Descrição |
| --- | --- | --- |
| `fonte` | varchar | Fonte oficial do registro. |
| `norma_id` | bigint | Código da norma no Senado. |
| `tipo_sigla` | varchar | Sigla do tipo da norma na fonte (LEI-n, DEC-n, MPV-cs...). |
| `tipo` | varchar | Tipo da norma (lei numerada, decreto numerado, decreto legislativo etc.). |
| `numero` | varchar | Número da norma, como a fonte informa (pode ter letra). |
| `ano` | integer | Ano de assinatura. |
| `assinada_em` | date | Data de assinatura; vazia quando a fonte não informa. |
| `nome` | varchar | Nome oficial (por exemplo, Lei nº 14.116 de 31/12/2020). |
| `identificador` | varchar | Identificador curto da norma na fonte (LEI-14116-2020-12-31). |
| `ementa` | varchar | Ementa com caixa padronizada. |
| `ementa_oficial` | varchar | Ementa exatamente como a fonte publica. |
| `apelido` | varchar | Apelido popular quando a fonte informa (por exemplo, Lei de Diretrizes Orçamentárias - LDO 2021). |
| `fonte_url` | varchar | Página oficial da norma no Senado. |
| `capturado_em` | date | Data da captura do arquivo de origem. |

### marts.normas_geradas

| Coluna | Tipo | Descrição |
| --- | --- | --- |
| `fonte` | varchar | Fonte oficial do registro. |
| `proposicao_id` | varchar | Matéria (marts.proposicoes, junto com a fonte). |
| `norma_id` | bigint | Código da norma no Senado (marts.normas). |
| `tipo` | varchar | Tipo da norma (lei, emenda constitucional, decreto legislativo etc.). |
| `numero` | integer | Número da norma. |
| `ano` | integer | Ano de assinatura da norma. |
| `assinada_em` | date | Data de assinatura. |
| `publicada_em` | date | Data de publicação. |
| `descricao` | varchar | Descrição oficial da norma. |
| `veiculo_publicacao` | varchar | Veículo de publicação (por exemplo, DOU). |
| `capturado_em` | date | Data da captura do lote de origem. |

### marts.normas_publicacoes

| Coluna | Tipo | Descrição |
| --- | --- | --- |
| `fonte` | varchar | Fonte oficial do registro. |
| `norma_id` | bigint | Norma publicada (marts.normas). |
| `publicacao_id` | bigint | Código da publicação no Senado. |
| `tipo_sigla` | varchar | Tipo da publicação (PUB original, VEP veto parcialmente rejeitado etc.). |
| `veiculo` | varchar | Veículo e edição, como a fonte informa. |
| `publicada_em` | date | Data da publicação. |
| `pagina` | varchar | Página da publicação. |
| `coluna` | varchar | Coluna da página. |
| `tem_texto` | boolean | A fonte informa que há o texto da publicação. |
| `capturado_em` | date | Data da captura do arquivo de origem. |

### marts.normas_relacoes

| Coluna | Tipo | Descrição |
| --- | --- | --- |
| `fonte` | varchar | Fonte oficial do registro. |
| `norma_id` | bigint | Norma de que se fala (marts.normas). |
| `tipo_relacao` | varchar | Tipo da relação como a fonte declara (por exemplo, Declaração de Alteração Permanente). |
| `norma_posterior_id` | bigint | Ato posterior que se relaciona com a norma. |
| `norma_posterior_nome` | varchar | Nome do ato posterior. |
| `norma_posterior_assinada_em` | date | Data de assinatura do ato posterior. |
| `publicada_em` | date | Data de publicação do ato posterior. |
| `publicacao` | varchar | Publicação do ato posterior no Diário Oficial. |
| `capturado_em` | date | Data da captura do arquivo de origem. |

### marts.ocupacoes

| Coluna | Tipo | Descrição |
| --- | --- | --- |
| `id_pessoa` | bigint | Chave da pessoa (marts.pessoas). |
| `titulo` | varchar | Ocupação declarada. |
| `entidade` | varchar | Entidade em que exerceu a ocupação. |
| `entidade_uf` | varchar | UF da entidade. |
| `ano_inicio` | integer | Ano de início. |
| `ano_fim` | integer | Ano de fim. |

### marts.orgaos

| Coluna | Tipo | Descrição |
| --- | --- | --- |
| `fonte` | varchar | Fonte oficial do registro. |
| `orgao_id` | bigint | Identificador do órgão na fonte. |
| `sigla` | varchar | Sigla do órgão. |
| `apelido` | varchar | Nome curto do órgão. |
| `nome` | varchar | Nome oficial do órgão. |
| `tipo` | varchar | Tipo do órgão segundo a fonte. |
| `inicio` | date | Início do órgão, quando a fonte informa. |
| `instalado_em` | date | Data de instalação, quando a fonte informa. |
| `fim` | date | Fim do órgão, quando a fonte informa. |
| `situacao` | varchar | Situação do órgão segundo a fonte. |
| `casa` | varchar | Casa legislativa informada pela fonte; vazia quando não informa. |
| `fonte_url` | varchar | Endereço do órgão na fonte oficial. |

### marts.partidos

| Coluna | Tipo | Descrição |
| --- | --- | --- |
| `fonte` | varchar | Fonte oficial do registro. |
| `partido_id` | bigint | Identificador do partido na fonte. |
| `sigla` | varchar | Sigla do partido. |
| `nome` | varchar | Nome do partido, com caixa padronizada. |

### marts.pessoas

| Coluna | Tipo | Descrição |
| --- | --- | --- |
| `id_pessoa` | bigint | Chave própria e estável da pessoa (schema identity). |
| `fonte` | varchar | Fonte principal do cadastro da pessoa (camara ou senado). |
| `fontes` | varchar | Todas as fontes em que a pessoa aparece (por exemplo, camara, senado). |
| `nome` | varchar | Nome parlamentar, com caixa padronizada. |
| `nome_civil` | varchar | Nome civil, com caixa padronizada. |
| `nome_ordem` | varchar | Nome sem acento e em minúsculas, para ordenar. |
| `nome_busca` | varchar | Nome e nome civil sem acento, para buscar. |
| `sexo` | varchar | Sexo registrado no cadastro da fonte. |
| `data_nascimento` | date | Data de nascimento informada pela fonte. |
| `data_falecimento` | date | Data de falecimento informada pela fonte. |
| `municipio_nascimento` | varchar | Município de nascimento informado pela fonte. |
| `uf_nascimento` | varchar | UF de nascimento informada pela fonte. |
| `foto_url` | varchar | Endereço da foto oficial. |
| `rede_social_url` | varchar | Primeira rede social informada no cadastro. |
| `site_url` | varchar | Site informado no cadastro. |
| `primeira_legislatura_com_voto` | integer | Primeira legislatura em que há voto registrado. |
| `ultima_legislatura_com_voto` | integer | Última legislatura em que há voto registrado. |
| `profissoes` | varchar | Profissões declaradas, separadas por ponto e vírgula. |
| `ultimo_partido` | varchar | Partido no voto mais recente. |
| `ultima_uf` | varchar | UF no voto mais recente. |
| `ultimo_voto_em` | timestamp | Data e hora do voto mais recente. |
| `qtd_propostas` | bigint | Quantidade de proposições em que consta como autora ou apoiadora; vazio onde a fonte não informa autoria (Senado). |
| `qtd_votos` | bigint | Quantidade de votos nominais registrados. |
| `capturado_em` | date | Data da captura do cadastro de deputados. |

### marts.proposicoes

| Coluna | Tipo | Descrição |
| --- | --- | --- |
| `fonte` | varchar | Fonte oficial do registro (por exemplo, camara). |
| `proposicao_id` | varchar | Identificador da proposição na fonte. |
| `sigla` | varchar | Sigla do tipo da proposição, número e ano. |
| `ementa` | varchar | Ementa padronizada (caixa); igual à oficial quando já estava em caixa mista. |
| `ementa_oficial` | varchar | Texto oficial, exatamente como veio. |
| `apresentada_em` | date | Data de apresentação. |
| `situacao` | varchar | Situação atual segundo a fonte. |
| `orgao_ultimo_status` | varchar | Órgão do último andamento. |
| `ultimo_status_em` | date | Data do último andamento. |
| `fonte_url` | varchar | Endereço da proposição na fonte oficial. |
| `capturado_em` | date | Data da captura do arquivo de origem. |

### marts.tramitacoes

| Coluna | Tipo | Descrição |
| --- | --- | --- |
| `fonte` | varchar | Fonte oficial do registro. |
| `proposicao_id` | varchar | Proposição (marts.proposicoes, junto com a fonte). |
| `sequencia` | integer | Número do andamento dentro da proposição. |
| `registrada_em` | timestamp | Data e hora do andamento. |
| `orgao_sigla` | varchar | Órgão em que ocorreu. |
| `regime` | varchar | Regime de tramitação informado. |
| `descricao` | varchar | Descrição do tipo de andamento. |
| `situacao` | varchar | Situação da proposição após o andamento. |
| `despacho` | varchar | Texto do despacho, como a fonte informa. |
| `capturado_em` | date | Data da captura do lote de origem. |

### marts.vetos

| Coluna | Tipo | Descrição |
| --- | --- | --- |
| `fonte` | varchar | Fonte oficial do registro. |
| `veto_id` | bigint | Código do veto no Senado. |
| `materia_veto_id` | bigint | Código da matéria do veto (a que tramita no Congresso). |
| `numero` | integer | Número do veto no ano. |
| `ano` | integer | Ano do veto. |
| `materia_vetada_id` | bigint | Código da matéria vetada (o projeto aprovado). |
| `materia_vetada_sigla` | varchar | Sigla da matéria vetada (PL, PLN, PLP...). |
| `materia_vetada_numero` | varchar | Número da matéria vetada. |
| `materia_vetada_ano` | integer | Ano da matéria vetada. |
| `materia_vetada_ementa` | varchar | Ementa da matéria vetada, com caixa padronizada. |
| `norma_id` | bigint | Norma gerada pela matéria (marts.normas); vazia quando não houve. |
| `norma_nome` | varchar | Nome da norma gerada. |
| `mensagem_numero` | integer | Número da mensagem presidencial do veto. |
| `mensagem_ano` | integer | Ano da mensagem presidencial. |
| `mensagem_url` | varchar | Mensagem presidencial no Planalto, como a fonte informa. |
| `veto_total` | boolean | Veto total (verdadeiro) ou parcial (falso). |
| `assunto` | varchar | Assunto do veto, como a fonte informa. |
| `recebido_em` | date | Data em que o Congresso recebeu o veto. |
| `publicado_em` | date | Data de publicação do veto. |
| `sobrestado_em` | date | Data em que o veto passou a trancar a pauta. |
| `sobrestando_pauta` | boolean | O veto tranca a pauta hoje. |
| `quantidade_dispositivos` | integer | Quantos dispositivos foram vetados. |
| `em_tramitacao` | boolean | O veto ainda tramita. |
| `fonte_url` | varchar | Página oficial da matéria do veto no Senado. |
| `capturado_em` | date | Data da captura do arquivo de origem. |

### marts.votacoes

| Coluna | Tipo | Descrição |
| --- | --- | --- |
| `fonte` | varchar | Fonte oficial do registro. |
| `votacao_id` | varchar | Identificador da votação na fonte. |
| `data` | date | Data da votação. |
| `orgao_sigla` | varchar | Sigla do órgão em que ocorreu. |
| `descricao` | varchar | Descrição oficial da votação, com caixa padronizada. |
| `aprovada` | integer | 1 se a fonte registra aprovação; 0 se não; vazio se não informa. |
| `votos_sim` | integer | Total de votos Sim informado pela fonte. |
| `votos_nao` | integer | Total de votos Não informado pela fonte. |
| `votos_outros` | integer | Total de outros votos informado pela fonte. |
| `proposicoes` | varchar | Proposições ligadas à votação, separadas por ponto e vírgula. |
| `votacao_secreta` | boolean | Verdadeiro se a votação foi secreta; vazio onde a fonte não informa (Câmara). |
| `capturado_em` | date | Data da captura do arquivo de origem. |

### marts.votos

| Coluna | Tipo | Descrição |
| --- | --- | --- |
| `fonte` | varchar | Fonte oficial do registro. |
| `id_pessoa` | bigint | Chave da pessoa (marts.pessoas). |
| `votacao_id` | varchar | Votação (marts.votacoes, junto com a fonte). |
| `voto` | varchar | Voto registrado pela fonte (Sim, Não, Abstenção, Obstrução etc.). |
| `votou_em` | timestamp | Data e hora do voto. |
| `partido` | varchar | Partido na data do voto. |
| `uf` | varchar | UF na data do voto. |

### marts.votos_de_candidatos

| Coluna | Tipo | Descrição |
| --- | --- | --- |
| `fonte` | varchar | Fonte oficial do registro. |
| `id_pessoa` | bigint | Chave da pessoa (marts.pessoas). |
| `candidatura_id` | varchar | Candidatura (marts.candidaturas). |
| `ano_eleicao` | integer | Ano da eleição. |
| `turno` | integer | Turno da eleição. |
| `uf` | varchar | UF da candidatura. |
| `cargo` | varchar | Cargo disputado. |
| `votos_nominais` | bigint | Votos nominais recebidos, de qualquer destinação. |
| `votos_validos` | bigint | Votos nominais válidos. |
| `municipios` | bigint | Em quantos municípios o candidato teve votos. |
| `capturado_em` | date | Data da captura do arquivo de origem. |

### marts.votos_em_vetos

| Coluna | Tipo | Descrição |
| --- | --- | --- |
| `fonte` | varchar | Fonte oficial do registro. |
| `dispositivo_id` | bigint | Dispositivo votado (marts.dispositivos_vetados). |
| `casa` | varchar | Câmara ou Senado. |
| `nome_parlamentar` | varchar | Nome do parlamentar como a fonte informa, com caixa padronizada. |
| `partido` | varchar | Partido na sessão, como a fonte informa. |
| `uf` | varchar | UF do parlamentar. |
| `voto` | varchar | Voto como a fonte informa (Sim, Não, Branco, Abstenção...). |
| `sessao` | varchar | Sessão do Congresso, como a fonte informa. |
| `capturado_em` | date | Data da captura do arquivo de origem. |
