# Catálogo de fontes de dados abertas

Levantamento de 18/10/2026, feito por leitura das páginas oficiais e de algumas chamadas de teste; Câmara, Senado, TSE e a legislação federal (verificada em 23/10/2026) já estão carregados (ver [cobertura e lacunas](04-cobertura-e-lacunas.md)) e os termos de uso dos dois foram verificados em 21/10/2026. **Para as demais fontes, nada foi baixado em volume nem validado contra os dados.** Itens marcados "não confirmado" precisam ser checados antes de entrar em um pipeline. Páginas que a ferramenta de pesquisa não conseguiu abrir (robots.txt ou desafio de acesso) aparecem como "não verificado", o que não significa que a fonte não exista.

## Prioridade de consumo

1. Câmara dos Deputados (núcleo do primeiro entregável)
2. Senado Federal (votos nominais e matérias)
3. Diário Oficial da União, para ligar a decisão à norma publicada
4. TSE, para identidade de candidatos e partidos
5. Município de São Paulo (Câmara Municipal e Querido Diário)
6. Portal da Transparência e TCU, em fases posteriores

## Federal

### Câmara dos Deputados (dados abertos)

- **Acesso:** API REST v2 (`https://dadosabertos.camara.leg.br/api/v2/...`, JSON e XML) e arquivos em lote por ano (CSV, XLSX, ODS, JSON, XML), atualizados diariamente (`https://dadosabertos.camara.leg.br/arquivos/{conjunto}/{formato}/...`).
- **Teste feito:** `proposicoes?siglaTipo=PEC&numero=221&ano=2019` devolve a PEC 221/2019 (id 2233802), com links de paginação.
- **Proposições:** completas a partir de 2001; de 1946 a 2000 só os tipos que podiam virar lei; de 1934 a 1945 de forma parcial. Também temas e autores (um autor pode não ser parlamentar; uma proposição aparece uma vez por autor).
- **Votações:** arquivos anuais com votações, votos por deputado, orientações de bancada (só plenário), objetos votados e proposições afetadas. O registro de voto traz o deputado com o partido na data (`siglaPartido`), o que ajuda a mostrar o partido no momento da votação.
- **Cobertura histórica de votos (testada):** arquivo de votações de 1999 existe (primeiro registro em 20/01/1999); arquivos de votos de 2001 e 2003 existem; o de 1995 não pôde ser obtido; o de 1999 falhou na consulta e fica **não confirmado**. A página da Câmara não informa o ano inicial.
- **Também em lote:** deputados, órgãos e composição por legislatura (desde a 51ª), eventos e presenças, frentes, mesas diretoras, e cota parlamentar (CEAP) desde 2008.
- **Licença e limites (verificado em 21/10/2026):** o FAQ diz que os dados são gratuitos e livres, que não há cadastro, que não há restrição a uso comercial e que dados pessoais de parlamentares e colaboradores ficam de fora (Ato da Mesa 45/2012). Não há licença formal nem limite de requisições publicados; a API é indicada para consultas pontuais e os arquivos em lote para conjuntos grandes.
- **Cuidado:** votação simbólica não tem voto individual (a página diz que alguns registros simbólicos existem, mas não é regra).

### Senado Federal (dados abertos)

- **Acesso:** web services em `https://legis.senado.leg.br/dadosabertos/` (documentação Swagger em `/api-docs/swagger-ui/index.html`) e catálogo completo em CSV (`https://www12.senado.leg.br/dados-abertos/geracsv`).
- **Votações:** `GET /votacao` traz votos individuais nominais (votos secretos aparecem só em total). Filtros por `dataInicio`/`dataFim` (sem outro filtro, no máximo 1 ano), `codigoMateria` ou `sigla`+`numero`+`ano`, `codigoParlamentar`. Sem filtros devolve os últimos 12 meses. Há também orientação de bancada por data (`/plenario/votacao/orientacaoBancada/...`) e vetos do Congresso.
- **Colegiados (verificado em 12/11/2026):** `GET /dados/ListaColegiados.json` (`/comissao/lista/colegiados` redireciona para ele) lista código, sigla, nome, tipo, casa e início dos colegiados **em atividade** do Senado e do Congresso (comissões, plenário, conselhos, comitês); o extinto não consta. Vira parte de `dim_orgaos` (`id_orgao` `senado-<código>`), declarado em `sources/legislativo/federal/senado.yml`. A votação do Senado traz só a sigla do colegiado, então `fct_votacoes.id_orgao` liga por ela, quando a sigla identifica um colegiado em atividade.
- **Matérias:** `GET /processo` com filtros por sigla, número, ano, autor, datas; detalhes por processo (autoria, tramitações, textos), relatorias, emendas e documentos.
- **CSVs:** vários só cobrem o último ano ou o que está em tramitação.
- **Cobertura histórica:** a página não informa. **Não confirmado** a partir de que ano há votos nominais em formato aberto.
- **Licença e limites (verificado em 21/10/2026):** os dados são "disponibilizados sob licença que permita sua livre utilização", sem nomear a licença; a política de uso do portal não pôde ser lida; sem cadastro e sem limite de requisições informado.

### Diário Oficial da União (DOU) (verificado em 23/10/2026)

- **Acesso (verificado em 24/10/2026):** a página `https://www.in.gov.br/acesso-a-informacao/dados-abertos/base-de-dados?ano=2026&mes=Outubro` traz, no HTML, os links diretos de um zip por seção (`S01` atos normativos, `S02` atos de pessoal, `S03` contratos, editais e avisos). No mês corrente o nome muda a cada atualização (`S01102026_Atualizado185748.zip`); nos meses fechados é fixo (`S01082026.zip`). O pedido precisa do cabeçalho `Accept: */*` (sem ele, a página responde 403). O INLABS (credencial) estava em manutenção e o dados.gov.br respondeu 401.
- **Conteúdo medido (ago a out de 2026):** cada zip tem um XML por matéria (`<edição>_<AAAAMMDD>_<id>.xml`, com tipo, órgão, data, ementa e texto) e imagens. Agosto: 8.590, 16.368 e 49.642 XMLs nas seções 1, 2 e 3; setembro: 8.927, 16.454 e 47.698; outubro até o dia 23: 6.287, 11.474 e 36.900. Os dias cobertos batem com os dias úteis (mais edições extras na seção 1).
- **Limites:** o XML aberto **não substitui a versão certificada** (o PDF). O dicionário de dados **não existe**. Cobertura anterior a 2026 e tamanho do histórico: de janeiro a outubro de 2026 são cerca de 4,1 GB em 30 zips; os anos anteriores não foram verificados.
- **Licença:** o site declara **Creative Commons Atribuição-SemDerivações 3.0 (CC BY-ND)**. Guardar o arquivo original e lê-lo é livre; redistribuir trecho modificado, não. Por isso o projeto guarda só o landing e não transforma o texto em tabelas ([ADR 0019](../05-decisoes/0019-dou-so-no-landing.md)).
- **Uso aqui:** só o landing, por mês, de agosto de 2026 em diante. Depois, índice privado para busca semântica (RAG), sempre com o link da fonte e a data, e resposta de IA rotulada como tal.

### TSE (dados abertos)

- **Acesso:** `https://dadosabertos.tse.jus.br/` com 187 conjuntos em arquivos, principalmente CSV, e catálogo CKAN (`/api/3/action/package_show?id=candidatos-2022`). Não há API de consulta.
- **Conteúdo:** candidaturas (inclui bens, coligações, redes sociais, fotos e certidões criminais), prestação de contas, resultados por município, zona e seção, eleitorado, dados processuais.
- **Licença (verificado em 21/10/2026):** cada conjunto declara Creative Commons Attribution (CC BY): citar a fonte. Os pacotes de candidaturas de cada eleição têm cerca de 3 a 5 MB; o arquivo `_BRASIL.csv` dentro do pacote reúne os estados.
- **Complementar (verificado em 23/10/2026):** `bem_candidato_{ano}.zip` (bens declarados, de 2006 a 2026, 31 MB no total; 1998 e 2002 não existem; 2006 e 2010 usam outros nomes de coluna) e `votacao_candidato_munzona_{ano}.zip` (votos de cada candidato por município e zona, de 1998 a 2026, **2,4 GB compactados**; 2022 sozinho tem 580 MB, 4,3 GB descompactados e 9,38 milhões de linhas, de todos os cargos). Os dois trazem `SQ_CANDIDATO`, a chave que liga à candidatura.
- **Cuidado:** são dados pessoais de candidatos. As certidões criminais não entram; CPF, título de eleitor e e-mail nunca entram. Já carregados (30/10/2026): nome social, bens, coligações, fotos e a prestação de contas de 2018, 2022 e 2026. Fora da carga por enquanto: redes sociais, propostas, notas fiscais e a prestação de contas das demais eleições (issue 150).

### TSE: eleições gerais de 2026 (verificado em 25/10/2026)

- **Portal de dados abertos** (`dadosabertos.tse.jus.br`, CC BY, acessível por robô): `candidatos-2026` (candidaturas, bens, coligações, vagas, redes sociais, fotos), `resultados-2026` (votação nominal por município e zona, detalhe da apuração, votação por seção) e `prestacao-de-contas-eleitorais-2026` (receitas e despesas de candidatos e partidos). Os pacotes `.zip` ficam em `cdn.tse.jus.br/estatistica/sead/odsele/...` e o servidor informa `ETag` e `Last-Modified`.
- **Vagas** (`consulta_vagas_{ano}.zip`): quantas vagas cada cargo tem por unidade eleitoral (2026: 54 de senador, 513 de deputado federal, 27 de governador). O arquivo de 2022 traz também a eleição suplementar de governador de Roraima (código 6278).
- **Prestação de contas de candidatos** (`prestacao_de_contas_eleitorais_candidatos_{ano}.zip`): uma linha por receita e por despesa; o pacote de 2026 tem 201 MB compactados e o de 2022, mais de 1,7 GB descompactados nos arquivos usados. Traz documento e nome de doadores e fornecedores, que a plataforma não lê.
- **Não acessíveis por robô:** a página de informações técnicas da divulgação de resultados (`www.tse.jus.br`) e o DivulgaCandContas (propostas de governo) respondem 403 do Akamai, mesmo com cabeçalhos honestos; não foram contornados. O JSON de divulgação em tempo real (`resultados.tse.jus.br`) não teve o formato verificado.

### Portal da Transparência (CGU) (verificado em 23/10/2026)

- **Acesso:** API com token gratuito (conta gov.br nível prata ou ouro; cabeçalho `chave-api-dados`). Limite informado: 400 requisições por minuto entre 6h e 23h59 e 700 por minuto entre 0h e 5h59. Download em lote em `/download-de-dados/...`, **sem token**.
- **Emendas parlamentares:** `/download-de-dados/emendas-parlamentares/UNICO` devolve um zip nacional de 32,5 MB, atualizado todo dia (`ETag` e `Last-Modified`), com três tabelas em latin-1: emendas (94.736 linhas, de 2014 a 2026), convênios (85.403) e favorecidos (828.419). O autor vem pelo nome e por um código orçamentário (1.614 autores; 15.962 emendas sem autor, sobretudo as antigas), que não é o código do parlamentar: a emenda não se liga a `pessoas`.
- **Privacidade:** 181.509 favorecidos são **pessoas físicas** (cidadãos comuns, com nome e CPF mascarado) e mais alguns milhares são "inscrição genérica": nunca entram; só pessoa jurídica (CNPJ) e unidade gestora.
- **Despesas e contratos (lidos em 03/11/2026, um mês de amostra, 2025-10):** o endereço `/download-de-dados/despesas-execucao/AAAAMM` do portal redireciona (302) para o host de arquivos `dadosabertos-download.cgu.gov.br/PortalDaTransparencia/saida/...`; o projeto usa a URL direta, porque a regra de bloqueio do [ADR 0038](../05-decisoes/0038-cortesia-e-bloqueio-na-ingestao.md) trata o redirecionamento para outro site como bloqueio. Um zip por mês, CSV em latin-1 separado por `;`, vírgula decimal; captura de 2022-11 em diante (4 anos), com `rate_limit: 0.03` (uma requisição a cada ~33 s; a 5 s o portal bloqueou com HTTP 405 após 12 a 17 arquivos) e `lag_months: 1` (só meses fechados). Em 03/11/2026, depois de 12 meses baixados, o GET passou a responder **HTTP 405**: o projeto passou a tratar 405 como bloqueio e a baixar o `Compras.zip` uma vez para os três datasets ([ADR 0045](../05-decisoes/0045-meses-fechados-405-e-pacote-unico.md)).
  - **Despesas** (`saida/despesas-execucao/AAAAMM_Despesas.zip`, 7,8 MB por mês): 47 colunas, uma linha por órgão, unidade gestora, ação e natureza da despesa, com os valores empenhado, liquidado e pago no mês. **Não traz favorecido** (a issue 11 pedia empenho por favorecido; este arquivo é a execução agregada). O nome da coluna da fonte `Código Subfução` tem erro de grafia e é mantido.
  - **Contratos** (`saida/compras/AAAAMM_Compras.zip`, 1 MB por mês, quatro CSVs): `Compras` (24 colunas, um contrato por linha), `ItemCompra`, `TermoAditivo` e `Apostilamento` (praticamente vazio na amostra; **não carregado**). **`Código Contratado` e `Nome Contratado` entram**: no mês de amostra (2025-10) 316 de 3.507 contratos tinham CPF completo (11 dígitos, sem máscara) no código do contratado. Por decisão do fundador, o raw (privado) guarda como a fonte publica e o staging, que vai ao lake, mascara com `mascarar_dado_pessoal` (ADR 0017; colunas `cd_contratado` e `contratado` com `pii: true`; `-11` e `Sigiloso` são os marcadores da fonte para contrato protegido por sigilo; issue 216). O texto livre (`Objeto`, descrições) passa por `mascarar_dado_pessoal` no staging.
  - **Licitações** (`saida/licitacoes/AAAAMM_Licitacoes.zip`, mensal, 3 a 8 MB; lidas em 10/11/2026, mês de amostra 2024-01): quatro CSVs em latin-1 com `;` e vírgula decimal, cada um um dataset que lê o mesmo zip (ADR 0045): `Licitação` (17 colunas, uma por unidade gestora, modalidade e número; 2.537 linhas na amostra), `ItemLicitação` (14; um item por vencedor), `ParticipantesLicitação` (13; um por item e participante, com `Flag Vencedor`) e `EmpenhosRelacionados` (10; vazio na amostra). Os nomes dos CSVs têm acento e o zip os grava em UTF-8, por isso o `member` casa só o começo (`*_Licita*.csv`). Achados na amostra, que o projeto mede em vez de corrigir: a fonte repete linhas idênticas em itens (3 de 51.808) e participantes (18 de 161.400), deixa `Código Item Compra` vazio em 96 itens (o código não é chave única do item), e `Código Participante` e `Código Vencedor` trazem, além de CNPJ (14 dígitos), CPF (11 dígitos; 57 participantes e 29 itens) e códigos de 3 dígitos que o dicionário não descreve. O CPF segue o padrão da fonte: completo no raw (privado), mascarado no staging e nos marts, com `fl_contem_dado_pessoal`. Em 10/11/2026 os meses 2024-01 e 2024-03 responderam 200, e meses mais recentes (2024-12, 2025-04 a 2026-10) responderam 403; a sondagem parou em HTTP 405 (bloqueio por rajada de HEAD), então **o último mês publicado não está confirmado** (ver ADR 0045: 403 em mês que não é o mais recente conta como bloqueio).
  - **Sanções (CEIS, CNEP, CEAF): não carregadas.** O arquivo muda de URL todo dia (`saida/ceis/AAAAMMDD_CEIS.zip`; só o do dia existe, o de ontem e `UNICO_CEIS.zip` respondem 403), o que o contrato de fonte ainda não expressa (issue 218).
- **Conteúdo do portal ainda não carregado:** benefícios (incluindo Bolsa Família), servidores, viagens, convênios (fora os de emendas) e sanções.
- **Licença:** livre utilização, conforme o Decreto 8.777/2016.
- **Termo de Uso do portal (lido em 27/10/2026, a partir do PDF que o fundador exportou de `https://portaldatransparencia.gov.br/termos-de-uso`; aviso de privacidade atualizado em 01/10/2024):** a seção 3 diz que o acesso "não requer usuário nem senhas, sendo permitido a qualquer cidadão navegar pelas páginas de forma livre, bem como visualizar e utilizar os dados disponíveis da forma que melhor lhe convier". O documento **não** define licença para os dados, **não** exige citação da fonte, **não** restringe uso comercial, redistribuição nem acesso automatizado e **não** fixa limite de requisições para o download em lote. A seção 4 responsabiliza o usuário pelos danos que causar a terceiros, inclusive a direitos de personalidade, o que pesa sobre o uso dos favorecidos pessoa física (ver o [documento de LGPD](../01-entender/07-lgpd-dados-pessoais.md)). O Aviso de Privacidade trata dos dados de quem **usa o site** (cookies, Google Analytics), não das pessoas que aparecem nos conjuntos de dados.
- **Dicionário de dados das emendas (lido em 27/10/2026, a partir do PDF exportado de `https://portaldatransparencia.gov.br/dicionario-de-dados/emendas-parlamentares`):** descreve as três tabelas que carregamos (por emenda, convênios e favorecidos). O que ele ensina e que conferi nos nossos dados:
  - **Código da emenda:** 12 dígitos, sendo 4 do ano, 4 do código do autor e 4 do número da emenda do autor. Nas 76.937 emendas com código, todas seguem essa estrutura (ano e código do autor batem). O código do autor é o do SIAFI, não o do parlamentar, o que confirma por que a emenda não se liga a `pessoas` sem uma regra própria (ADR 0028).
  - **Código do município IBGE:** é o código de **destinação do recurso**, em branco conforme a localidade de aplicação. Das 94.747 emendas, 37.710 trazem o código, e todas ligam a `dim_municipios` (5.424 municípios, 0 sem correspondência).
  - **Valor do convênio:** é a participação do concedente, somada à parcela 999 de rendimento de aplicação financeira, quando houver.
  - **Tipo do favorecido:** o dicionário cita só Pessoa Física e Pessoa Jurídica, mas os dados trazem também Unidade Gestora, Inscrição Genérica, Sem informação e Inválido (em parte das linhas a fonte grafa "Inscrição Genéric", truncado). A descrição da coluna agora lista os valores reais.
  - **Autor e favorecido:** o autor é "conforme registrado no SIAFI"; favorecidos são entes governamentais, entidades sem fins lucrativos, demais pessoas jurídicas ou pessoas físicas que receberam transferências de recursos públicos federais.
- **Ainda não lida:** a página de origem e atualização dos dados do portal (atrás da verificação anti-robô, não contornada). O portal aplica a verificação (AWS WAF) a requisições automáticas das páginas; o download em lote do arquivo de emendas segue funcionando sem ela.

### IBGE, localidades (verificado em 27/10/2026)

- **O quê:** a lista oficial dos 5.571 municípios (código do IBGE de 7 dígitos, nome, UF, região e hierarquia regional), a dimensão territorial da plataforma. Fonte declarada em `sources/executivo/federal/ibge.yml`; vira `dim_municipios`.
- **Onde:** API `https://servicodados.ibge.gov.br/api/v1/localidades/municipios` (documentação: `https://servicodados.ibge.gov.br/api/docs/localidades`), JSON sem autenticação.
- **Licença:** política de dados abertos do Poder Executivo federal (Decreto 8.777/2016). A página da API não traz termos de uso próprios.
- **Cuidado:** o servidor responde sempre comprimido (`Content-Encoding: gzip`), mesmo quando se pede sem compressão; o downloader descomprime e o landing guarda o JSON.
- **De-para com o TSE:** o TSE usa códigos próprios de município e não publica o do IBGE. `dim_municipios_codigos_tse` liga os dois por nome e UF, só quando o par é único dos dois lados: 5.556 dos 5.569 municípios do TSE ligam, e os 13 restantes (grafias diferentes, como "Barão de Monte Alto") ficam sem código do IBGE, medidos pelo teste `municipios_do_tse_sem_correspondencia_no_ibge`.

### Pessoas Expostas Politicamente (CGU), topo do Executivo federal (verificado em 12/11/2026)

- **O quê:** quem exerceu, nos últimos cinco anos, função pública relevante: nome, função, órgão, início e fim do exercício e fim da carência. Só entram Presidente, Vice-Presidente e Ministro de Estado (as outras ~133 mil linhas são descartadas na carga; o zip original fica no landing). Fonte declarada em `sources/executivo/federal/pep.yml`; vira `fct_executivo_ocupacoes` (issue 19).
- **Onde:** `https://portaldatransparencia.gov.br/download-de-dados/pep`, que redireciona para `https://dadosabertos-download.cgu.gov.br/PortalDaTransparencia/saida/pep/AAAAMM_PEP.zip` (um CSV latin-1 em `;`).
- **Licença:** política de dados abertos (Decreto 8.777/2016); a página do conjunto não declara licença própria. O DOU (CC BY-ND) não é usado; a página do Planalto com ex-presidentes e ex-ministros fica atrás de verificação anti-robô e não foi lida.
- **Cuidado:** o portal só mantém o arquivo do último mês publicado (o do mês fechado sai por volta do dia 21 do mês seguinte; os anteriores respondem 403), então o histórico além de cinco anos não existe e o landing é quem o preserva daqui em diante. O CPF, mascarado pela fonte, não é carregado: sem CPF nem nascimento, a pessoa não é ligada a `dim_pessoas` (a ligação por nome seria um palpite). `custom/executivo/federal/pep.py` trata o 403 de mês retirado como falha comum, e a fonte é separada do Portal da Transparência para que isso não interrompa despesas e contratos.

### TCU (verificado em 23/10/2026)

- **Acesso:** `https://sites.tcu.gov.br/dados-abertos/jurisprudencia/`, sem requisitos, com um manifesto legível por máquina (`arquivos/jurisprudencia-arquivos.csv`, atualizado em 02/10/2026) que lista cada arquivo CSV com ano e tamanho. Acórdãos de 1992 a 2026 (**7,65 GB**, de 15 MB a 500 MB por ano), jurisprudência selecionada (112 MB), respostas a consultas, súmulas, boletins e informativos (cerca de 20 MB). Há também "visões gerais" de acórdãos geradas com IA, que precisariam de rótulo próprio. Contas irregulares e certidões: não apareceram.
- **Termos:** o portal reserva os direitos autorais (Lei 9.610/98), **proíbe uso comercial sem autorização** e exige citar fonte, título e autor; não nomeia licença aberta nem trata de acesso automatizado. A página de dados abertos e os termos do portal se contradizem na prática.
- **Recomendação:** adiar. O ganho para o objetivo legislativo é pequeno e a licença não é aberta; antes de carregar, pedir autorização ao TCU.

### Legislação federal (verificado em 23/10/2026)

- **Normas, publicações e relações: API do Senado, `legislacao`** (`https://legis.senado.leg.br/dadosabertos/legislacao/...`, JSON). `lista?ano=` traz o catálogo por ano de assinatura (244.020 normas e atos distintos de 1808 a 2026, e as listas anuais repetem 511 entradas: 149 mil decretos numerados, 16,7 mil leis numeradas, 16 mil decretos sem número, 15,9 mil decretos legislativos, 12,4 mil decretos-lei, 7,5 mil medidas provisórias, 240 leis complementares, 190 emendas constitucionais). O detalhe por código traz as publicações no Diário Oficial (edição, página e coluna) e as relações com atos posteriores (alteração, regulamentação, veto, declaração de constitucionalidade). Não traz o texto da lei.
- **Vetos: API do Senado e do Congresso.** `materia/vetos/{ano}` lista os vetos desde 1994 (1.350 até 2026; de 1988 a 1993 a API não devolve). `plenario/resultado/veto/materia/{código}` traz cada dispositivo vetado (texto vetado, razão do veto, situação: Mantido, Rejeitado, Prejudicado ou Não Apreciado). `plenario/resultado/veto/dispositivo/{código}` traz o voto nominal de deputados e senadores, **com nome, partido e UF, sem o código do parlamentar**.
- **Constituição: Câmara dos Deputados.** A página `constituicao1988` publica o texto atualizado em HTML (atualizado até a EC 141/2026) e o ADCT (até a EC 136), um arquivo cada, e o nome muda a cada emenda. O Senado entrega as relações da Constituição (641: 332 alterações permanentes, 133 regulamentações, 102 legislações correlatas) na própria API `legislacao` (norma 579494).
- **Limites e termos.** A API do Senado limita a 10 requisições por segundo (a plataforma usa 4) e pode devolver 429 e 503. O portal do Senado diz que o conteúdo "pode ser utilizado, desde que seja citada a fonte e para fins lícitos"; não nomeia licença. O `normas.leg.br` declara Creative Commons Atribuição 4.0 nos próprios metadados. O `robots.txt` da Câmara não restringe a página da Constituição.
- **Não confirmado.** O texto integral das leis comuns: não vem na API documentada, o link de publicação devolve PDF vazio e a rota interna do `normas.leg.br` (`/api/public/normas`) não é documentada e respondeu 400. O Planalto não abre desta rede (conexão derrubada) e o LexML está atrás de verificação anti-robô; nenhum dos dois foi contornado. As Constituições de 1824 a 1967 estão no catálogo, sem texto.

### Judiciário: composição dos tribunais (verificado em 12/11/2026; issue 69)

Pesquisa limitada por cortesia (poucas requisições por site, depois de bloqueios em outras fontes). **Não há fonte estruturada confirmada; nada foi implementado.**

- **STF** (`https://portal.stf.jus.br/ministros/`): a página responde 200, mas o HTML estático não traz a lista de ministros (carregada por script) e o painel "Corte Aberta" (`transparencia.stf.jus.br/extensions/corte_aberta/corte_aberta.html`) respondeu **403** a requisição automatizada. Sem dados abertos de composição, licença nem API encontrados. Ler a página exigiria robô com navegador: inviável pelo critério do projeto (sem robô nem captcha).
- **CNJ:** a página de dados abertos do portal (`cnj.jus.br/transparencia/dados-abertos/`) respondeu **403**, e `dadosabertos.cnj.jus.br` não respondeu. A Portaria CNJ de dados abertos define dado aberto como de uso livre com atribuição, mas não prova a licença de um conjunto de magistrados. O **DataJud** (`api-publica.datajud.cnj.jus.br`) exige chave e trata de **processos**, não de composição de tribunal. O Painel de Remuneração dos Magistrados é um painel com filtros, não um arquivo de cadastro.
- **TST** (`https://www.tst.jus.br/ministros`): a página estática cita ministros, mas é HTML de leiame sem contrato (cada tribunal tem leiaute próprio, sem licença declarada); não foi lida campo a campo. STJ e TSE: páginas institucionais sem arquivo aberto de composição encontrado (o `dadosabertos.tse.jus.br` só tem candidaturas e prestação de contas, já carregadas).
- **Complemento por outro poder:** a sabatina e a aprovação de ministros passam pelo Senado, que publica dados abertos (já usados na fonte `senado`); não verificado se a API traz indicações de autoridades.
- **Caminho proposto (decisão do fundador):** (1) uma tabela de referência em `dbt/seeds/` com as cadeiras previstas na Constituição (STF: 11, art. 101; STJ: no mínimo 33, art. 104), cada linha citando a página oficial do tribunal e a data de captura, conferida por pessoa; ela é dado de referência com fonte, não carga automática, e o teste mede cadeiras ocupadas contra o previsto; (2) em paralelo, pedir ao STF e ao CNJ um arquivo de composição com licença; (3) verificar a API do Senado para indicação e sabatina. Sem partido e sem juízo sobre os ministros (ADR 0054).

## Município de São Paulo

### Câmara Municipal de São Paulo

Programa de Dados Abertos criado pelo Ato da Mesa 1156/2011, que define dado aberto como de uso, reuso e distribuição livres, com no máximo exigência de atribuição e compartilhamento pela mesma licença.

| Conjunto | Formato | Observação |
| --- | --- | --- |
| SPLEGIS (processo legislativo, proposições) | Web service SOAP (`https://splegisws.saopaulo.sp.leg.br/ws/ws2.asmx`) | Fonte atual de proposições |
| Presença em plenário | XML | Por data, mês ou sessão legislativa |
| Votações em plenário | XML | Descrito como acumulado por sessão legislativa **do ano corrente**: pode não haver histórico. **Não confirmado** |
| Vereadores 1948–2017 | TXT | Obsoleto, encerrado em 2017 |
| Projetos 1948–1991 (lista, assuntos, autores) | TXT | Histórico, fora do SPLEGIS |
| Custos de mandato (SisGV) | Web service SOAP | Séries históricas 2007–2017 em ZIP |
| Relação de funcionários | XML, mensal | |

Lacunas prováveis: histórico de votos de vereadores e atas em formato estruturado. Pode ser necessário combinar com Lei de Acesso à Informação e com os diários oficiais.

### Diários oficiais (Querido Diário)

- **Acesso:** API pública (`https://api.queridodiario.ok.org.br/docs`). Código MIT; informações publicadas em CC BY 4.0.
- **Cobertura:** segundo um ensaio de Schneier, raspadores para 469 municípios; as páginas lidas não dizem se **São Paulo capital** está incluída. **Não confirmado.**
- **Uso aqui:** localizar leis e atos municipais e ligá-los às proposições.

### Prefeitura de São Paulo

- O portal de dados da Prefeitura (`dados.prefeitura.sp.gov.br`) e o Diário Oficial da Cidade **não puderam ser verificados** (a página exigiu um desafio de acesso).

## Pistas ainda não verificadas

Base dos Dados (dados tratados em BigQuery), Brasil.IO e iniciativas de acesso programático aos dados públicos. Podem reduzir trabalho, mas não substituem a fonte oficial: a regra do projeto é citar o documento original.

## Problemas de integração a resolver desde o início

1. **Identidade de pessoas entre fontes.** A Câmara, o Senado e o TSE usam identificadores diferentes. Unir "a mesma pessoa" é a parte difícil e precisa de regra explícita e auditável.
2. **Partido no momento do fato.** Parlamentares mudam de partido; guardar o partido da data do voto, como a Câmara já registra.
3. **Cobertura desigual no tempo.** Votos individuais confirmados em 2001 e 2003 para a Câmara; antes disso e em outras casas, cobertura por confirmar. Decisões antigas entram por curadoria manual rotulada.
4. **Votação simbólica e voto secreto.** A página deve mostrar "sem voto individual" em vez de preencher.
5. **Mudanças de formato e instabilidade.** Guardar sempre o bruto, testar contratos com respostas gravadas e rodar verificação diária contra a API real.
