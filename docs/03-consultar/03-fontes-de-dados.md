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
- **Cuidado:** são dados pessoais de candidatos. O nome social e as certidões criminais não entram; CPF, título de eleitor e e-mail nunca entram. Fora da carga por enquanto: redes sociais, fotos, propostas, notas fiscais e prestação de contas.

### TSE: eleições gerais de 2026 (verificado em 25/10/2026)

- **Portal de dados abertos** (`dadosabertos.tse.jus.br`, CC BY, acessível por robô): `candidatos-2026` (candidaturas, bens, coligações, vagas, redes sociais, fotos), `resultados-2026` (votação nominal por município e zona, detalhe da apuração, votação por seção) e `prestacao-de-contas-eleitorais-2026` (receitas e despesas de candidatos e partidos). Os pacotes `.zip` ficam em `cdn.tse.jus.br/estatistica/sead/odsele/...` e o servidor informa `ETag` e `Last-Modified`.
- **Vagas** (`consulta_vagas_{ano}.zip`): quantas vagas cada cargo tem por unidade eleitoral (2026: 54 de senador, 513 de deputado federal, 27 de governador). O arquivo de 2022 traz também a eleição suplementar de governador de Roraima (código 6278).
- **Prestação de contas de candidatos** (`prestacao_de_contas_eleitorais_candidatos_{ano}.zip`): uma linha por receita e por despesa; o pacote de 2026 tem 201 MB compactados e o de 2022, mais de 1,7 GB descompactados nos arquivos usados. Traz documento e nome de doadores e fornecedores, que a plataforma não lê.
- **Não acessíveis por robô:** a página de informações técnicas da divulgação de resultados (`www.tse.jus.br`) e o DivulgaCandContas (propostas de governo) respondem 403 do Akamai, mesmo com cabeçalhos honestos; não foram contornados. O JSON de divulgação em tempo real (`resultados.tse.jus.br`) não teve o formato verificado.

### Portal da Transparência (CGU) (verificado em 23/10/2026)

- **Acesso:** API com token gratuito (conta gov.br nível prata ou ouro; cabeçalho `chave-api-dados`). Limite informado: 400 requisições por minuto entre 6h e 23h59 e 700 por minuto entre 0h e 5h59. Download em lote em `/download-de-dados/...`, **sem token**.
- **Emendas parlamentares:** `/download-de-dados/emendas-parlamentares/UNICO` devolve um zip nacional de 32,5 MB, atualizado todo dia (`ETag` e `Last-Modified`), com três tabelas em latin-1: emendas (94.736 linhas, de 2014 a 2026), convênios (85.403) e favorecidos (828.419). O autor vem pelo nome e por um código orçamentário (1.614 autores; 15.962 emendas sem autor, sobretudo as antigas), que não é o código do parlamentar: a emenda não se liga a `pessoas`.
- **Privacidade:** 181.509 favorecidos são **pessoas físicas** (cidadãos comuns, com nome e CPF mascarado) e mais alguns milhares são "inscrição genérica": nunca entram; só pessoa jurídica (CNPJ) e unidade gestora.
- **Conteúdo do portal:** despesas, contratos, convênios, licitações, benefícios (incluindo Bolsa Família), sanções, servidores, viagens. Despesas (empenhos) e o resto: tamanho **não medido**.
- **Licença:** livre utilização, conforme o Decreto 8.777/2016. As páginas de dicionário de dados, termos de uso e origem dos dados pedem verificação anti-robô e **não foram lidas** (não foram contornadas).

### IBGE, localidades (verificado em 27/10/2026)

- **O quê:** a lista oficial dos 5.571 municípios (código do IBGE de 7 dígitos, nome, UF, região e hierarquia regional), a dimensão territorial da plataforma. Fonte declarada em `sources/executivo/federal/ibge.yml`; vira `marts.municipios`.
- **Onde:** API `https://servicodados.ibge.gov.br/api/v1/localidades/municipios` (documentação: `https://servicodados.ibge.gov.br/api/docs/localidades`), JSON sem autenticação.
- **Licença:** política de dados abertos do Poder Executivo federal (Decreto 8.777/2016). A página da API não traz termos de uso próprios.
- **Cuidado:** o servidor responde sempre comprimido (`Content-Encoding: gzip`), mesmo quando se pede sem compressão; o downloader descomprime e o landing guarda o JSON.
- **De-para com o TSE:** o TSE usa códigos próprios de município e não publica o do IBGE. `marts.municipios_codigos_tse` liga os dois por nome e UF, só quando o par é único dos dois lados: 5.556 dos 5.569 municípios do TSE ligam, e os 13 restantes (grafias diferentes, como "Barão de Monte Alto") ficam sem código do IBGE, medidos pelo teste `municipios_do_tse_sem_correspondencia_no_ibge`.

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
