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

## raw_federal_senado

| Tabela | O que é | Sensibilidade | Grain |
| --- | --- | --- | --- |
| `processos` | Processo de cada matéria votada, buscado por item na API (`_item` é o id do processo), só das já buscadas: situação atual e norma gerada. | publico-agente-publico |  |
| `processos__autoria_iniciativa` | Autoria de cada processo (lista `autoriaIniciativa`). | publico-agente-publico |  |
| `senadores` | Senadores por legislatura (o mesmo senador aparece em várias), com os mandatos em tabelas filhas. | publico-agente-publico |  |
| `senadores_detalhe` | Detalhe de cada senador, buscado por item na API (`_item` é o código do senador): nascimento, naturalidade e foto, só dos já buscados. | publico-agente-publico |  |
| `votacoes` | Votações em plenário com resultado, totais e a matéria votada. | publico-agente-publico |  |
| `votacoes__votos` | Voto de cada senador em cada votação nominal (lista `votos` da votação). | publico-agente-publico |  |

## raw_federal_tse

| Tabela | O que é | Sensibilidade | Grain |
| --- | --- | --- | --- |
| `candidaturas` | Candidaturas a deputado federal e senador (e suplentes) nas eleições gerais, uma linha por candidatura. | publico-agente-publico |  |

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
| `stg_identity__pessoa_fusoes` | Chaves de pessoa absorvidas por outra quando se mostraram a mesma pessoa, uma linha por chave absorvida. | publico-agente-publico |  |
| `stg_identity__pessoa_identificadores` | Identificadores de cada pessoa em cada fonte. | publico-agente-publico |  |
| `stg_identity__pessoas` | Pessoas do projeto (chave própria). | publico-agente-publico |  |
| `stg_metadata__captures` | Capturas dos arquivos da fonte (um arquivo, uma linha). `source_file_id` liga as linhas do raw ao arquivo. | publico-agente-publico |  |
| `stg_senado__processos` | Processo de cada matéria votada (só as já buscadas), com a situação atual e a norma gerada. | publico-agente-publico |  |
| `stg_senado__senadores` | Senadores, uma linha por senador (o mais recente dos arquivos de legislatura), com nomes padronizados. | publico-agente-publico |  |
| `stg_senado__senadores_detalhe` | Detalhe de cada senador (só os já buscados), com nome civil, nascimento, naturalidade e foto. | publico-agente-publico |  |
| `stg_senado__votacoes` | Votações em plenário com resultado, totais e a matéria votada. Votação secreta tem `secreta` verdadeiro. | publico-agente-publico |  |
| `stg_senado__votos` | Voto de cada senador em cada votação nominal. Em votação secreta a sigla é "Votou". | publico-agente-publico |  |
| `stg_tse__candidaturas` | Candidaturas ao Congresso (deputado federal e senador, com suplentes) nas eleições gerais, uma linha por candidatura e turno. | publico-agente-publico |  |

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
| `candidaturas` | Candidaturas ao Congresso (deputado federal e senador, com suplentes) de quem já é pessoa do projeto, com partido, situação e resultado. Uma linha por candidatura e turno. | publico-agente-publico | pessoa |
| `frentes` | Frentes parlamentares, com legislatura de criação e coordenador. Uma linha por frente. | publico | frente parlamentar |
| `fusoes_de_pessoas` | Chaves de pessoa absorvidas por outra quando se mostraram a mesma pessoa (por exemplo, deputado que virou senador). Uma linha por chave absorvida. | publico-agente-publico | chave absorvida |
| `legislaturas` | Legislaturas da Câmara, com datas oficiais de início e fim. Uma linha por legislatura. | publico | legislatura |
| `mandatos` | Mandatos por legislatura, a partir de votos observados (início e fim oficiais vazios). Uma linha por pessoa e legislatura. | publico-agente-publico | pessoa e legislatura |
| `membros_de_frentes` | Participação de pessoas em frentes parlamentares, com o título e a legislatura. Uma linha por pessoa, frente, legislatura e título. | publico-agente-publico | pessoa |
| `membros_de_orgaos` | Participação de pessoas em órgãos da Câmara, com cargo e período. Uma linha por pessoa, órgão, cargo e período informado. | publico-agente-publico | pessoa |
| `normas_geradas` | Norma jurídica que resultou de uma matéria, com número, datas e veículo de publicação. Só o Senado informa por enquanto. Uma linha por matéria. | publico | matéria |
| `ocupacoes` | Ocupações anteriores declaradas. Uma linha por pessoa e ocupação. | publico-agente-publico | pessoa e ocupação |
| `orgaos` | Órgãos da Câmara (comissões, plenário, mesa diretora, conselhos), com tipo e situação. Uma linha por órgão. | publico | órgão |
| `partidos` | Partidos com sigla e nome oficiais. Uma linha por partido. | publico | partido |
| `pessoas` | Pessoas (agentes públicos) com perfil, contagens e último partido. Uma linha por pessoa. | publico-agente-publico | pessoa |
| `proposicoes` | Proposições com ementa padronizada, ementa oficial, situação atual e URL da fonte. Uma linha por proposição. | publico | proposição |
| `tramitacoes` | Andamentos das proposições que podem virar norma (só as já buscadas), na ordem em que ocorreram. Uma linha por proposição e sequência. | publico | proposição e sequência |
| `votacoes` | Votações com resultado oficial, totais e proposições. Uma linha por votação. | publico | votação |
| `votos` | Voto de cada pessoa em cada votação nominal, com partido e UF na data. Uma linha por pessoa e votação. | publico-agente-publico | pessoa e votação |

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

### marts.normas_geradas

| Coluna | Tipo | Descrição |
| --- | --- | --- |
| `fonte` | varchar | Fonte oficial do registro. |
| `proposicao_id` | varchar | Matéria (marts.proposicoes, junto com a fonte). |
| `tipo` | varchar | Tipo da norma (lei, emenda constitucional, decreto legislativo etc.). |
| `numero` | integer | Número da norma. |
| `ano` | integer | Ano de assinatura da norma. |
| `assinada_em` | date | Data de assinatura. |
| `publicada_em` | date | Data de publicação. |
| `descricao` | varchar | Descrição oficial da norma. |
| `veiculo_publicacao` | varchar | Veículo de publicação (por exemplo, DOU). |
| `capturado_em` | date | Data da captura do lote de origem. |

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
