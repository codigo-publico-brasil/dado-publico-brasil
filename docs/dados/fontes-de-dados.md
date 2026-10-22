# Catálogo de fontes de dados abertas

Levantamento de 18/10/2026, feito por leitura das páginas oficiais e de algumas chamadas de teste; Câmara e Senado já estão carregados (ver [cobertura e lacunas](cobertura-e-lacunas.md)) e os termos de uso dos dois foram verificados em 21/10/2026. **Para as demais fontes, nada foi baixado em volume nem validado contra os dados.** Itens marcados "não confirmado" precisam ser checados antes de entrar em um pipeline. Páginas que a ferramenta de pesquisa não conseguiu abrir (robots.txt ou desafio de acesso) aparecem como "não verificado", o que não significa que a fonte não exista.

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

### Diário Oficial da União (DOU)

- **Acesso:** o projeto INLABS da Imprensa Nacional (`https://github.com/Imprensa-Nacional/inlabs`) disponibiliza as edições completas em PDF e XML, gratuitamente desde 01/01/2020. Se há cadastro e qual a cobertura anterior a 2020: **não verificado** (a página do `in.gov.br` bloqueou a consulta).
- **Uso aqui:** ligar a decisão (lei, decreto, medida provisória) à publicação oficial.

### TSE (dados abertos)

- **Acesso:** `https://dadosabertos.tse.jus.br/` com 187 conjuntos em arquivos, principalmente CSV. Não há API.
- **Conteúdo:** candidaturas (inclui bens e coligações), prestação de contas, resultados por município, zona e seção, eleitorado, dados processuais.
- **Cobertura:** a página mostra 2018, 2020 e 2026; há marcações para 2022, 2024 e 2025. Séries mais antigas: **não confirmadas**. Filiação partidária: não apareceu na página.
- **Licença (verificado em 21/10/2026):** cada conjunto declara Creative Commons Attribution (CC BY): citar a fonte. Os pacotes de candidaturas de cada eleição têm cerca de 3 a 5 MB; o arquivo `_BRASIL.csv` dentro do pacote reúne os estados.
- **Cuidado:** são dados pessoais de candidatos (bens, redes sociais, fotos). Usar só o necessário e seguir a política de dados do projeto.

### Portal da Transparência (CGU)

- **Acesso:** API com token gratuito por e-mail. Limite informado: 400 requisições por minuto entre 6h e 23h59 e 700 por minuto entre 0h e 5h59. Download em lote em `/download-de-dados`.
- **Conteúdo:** emendas parlamentares, despesas, contratos, convênios, licitações, benefícios (incluindo Bolsa Família), sanções, servidores, viagens.
- **Licença:** livre utilização, conforme o Decreto 8.777/2016.
- **Uso aqui:** fase posterior (ligar parlamentares a emendas e dinheiro).

### TCU

- **Acesso:** `https://sites.tcu.gov.br/dados-abertos/`, sem requisitos. Conjuntos confirmados: jurisprudência (acórdãos, jurisprudência selecionada, publicações, respostas a consultas, súmulas) e normativos. Certidões e contas irregulares: não apareceram. Formatos, API e licença: **não confirmados**.

### Legislação (lead)

- O Senado mantém o "acervo do portal LexML" (legislação federal, estadual e municipal). **Não verificado.** Pode servir para ligar proposição a lei.

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
