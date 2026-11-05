# Decisões de arquitetura (ADRs)

Para quem quer saber **por que** algo é como é. Responde: quando uma decisão vira ADR, como ler um, quais valem hoje e onde achar cada assunto. O resumo do que vale hoje está em [`../01-entender/02-arquitetura.md`](../01-entender/02-arquitetura.md); o ADR traz o contexto e as alternativas.

## Quando vira ADR e como é escrito

- Vira ADR a decisão que **fixa ou muda a arquitetura, uma ferramenta, uma regra de dados ou a estrutura** do repositório, e que seria cara de desfazer. Dependência nova exige ADR. Correção de bug e ajuste de código não.
- Um arquivo por decisão, numerado em ordem: `NNNN-assunto.md`. Formato: Status, Data, (Substitui/Altera), **Contexto**, **Decisão**, **Alternativas consideradas**, **Consequências**.
- **Uma decisão aceita não é editada.** Se mudar, nasce um ADR novo que diz o que substitui ou altera; o antigo continua como registro, e a tabela abaixo mostra qual vale.
- Quem propõe é a pessoa ou o agente; quem aceita é o fundador.

## Situação e índice por assunto

**Vigente:** vale como escrito. **Em parte:** só o que o ADR seguinte não substituiu. **Proposto:** o ADR ainda não foi marcado como aceito. **Proposto (aprovado pelo fundador):** o fundador já aprovou e o ADR está implementado; vale como escrito, só falta a marcação formal de aceito (decisão do fundador).

**Nomes antigos:** os ADRs anteriores a 2026-11-02 citam os nomes antigos de `metadata` e `identity` (`runs`, `captures`, `source_checks`, `pessoa_identificador`...). O de/para está em [`../99-historico/renomeacao-dos-marts.md`](../99-historico/renomeacao-dos-marts.md).

### Processo e pilha

| ADR | Decisão | Situação |
| --- | --- | --- |
| [0001](0001-fases-e-portoes.md) | Trabalhar em fases com portões verificáveis | proposto |
| [0002](0002-pilha-tecnologica.md) | Pilha tecnológica do piloto | em parte (dados curados: [0014](0014-warehouse-lake-duckdb-e-postgres-de-servico.md)) |
| [0003](0003-ferramentas-de-seguranca-do-ci.md) | Ferramentas de segurança do CI | proposto |
| [0006](0006-adotar-dlt-dbt-e-dagster.md) | Adotar dlt, dbt-core e Dagster | vigente (pastas e nomes: [0007](0007-dois-pacotes-e-camadas-de-mercado.md)) |
| [0014](0014-warehouse-lake-duckdb-e-postgres-de-servico.md) | DuckDB calcula, PostgreSQL serve | em parte (o PostgreSQL de serviço foi substituído pelo [0038](0038-lake-como-unica-publicacao.md)) |
| [0034](0034-manter-duckdb-e-postgres.md) | Manter DuckDB e PostgreSQL; sem DuckLake nem arquivos separados por ora, com gatilhos para reabrir | substituído pelo [0038](0038-lake-como-unica-publicacao.md) |
| [0035](0035-lakehouse-publico-no-r2.md) | Lakehouse público no R2: Parquet em caminho estável, staging a marts, catálogo e manifesto; DuckDB só calcula | proposto; altera 0014 (item 1 e gatilho 6a) e 0033; item 7 detalhado no 0036 |
| [0036](0036-r2-privado-fonte-da-verdade-do-que-nao-se-reconstroi.md) | R2 privado é a fonte da verdade da identidade e do metadata; disco local descartável; landing só local por ora (risco aceito) | proposto; complementa 0014 (item 4) e 0035 (item 7) |
| [0037](0037-arquivos-no-lake-com-prefixo-arq.md) | Arquivos (DOU, fotos) no lake público: pasta `arq_` na camada da fonte, com tabela de controle `arq_<nome>.parquet`; publicar é opt-in por dataset | proposto (decisão do fundador); altera 0035 (item 7) e 0036 (fotos) |
| [0038](0038-cortesia-e-bloqueio-na-ingestao.md) | Cortesia em toda requisição, bloqueio sem insistência e partição mensal | aceito; complementa o [0012](0012-dataset-por-item-lotes-com-envelope.md) |
| [0038](0038-lake-como-unica-publicacao.md) | O lake é a única publicação: sem PostgreSQL de serviço, cada aplicação monta as suas consultas sobre os marts | proposto (decisão do fundador); substitui 0034 e altera 0014 e 0033 |
| [0039](0039-marts-como-camada-semantica.md) | Os marts são a camada semântica: regra de negócio nos marts (não nas `app_*`), mudança só aditiva, derivado sempre marcado | proposto (desenho aprovado pelo fundador); altera 0038 (itens 3 e 4) |
| [0040](0040-ocupacao-de-cargo.md) | Ocupação de cargo como fato (`fct_cargos_ocupacoes`): exercício publicado vence, mandato cobre o resto | proposto (desenho aprovado pelo fundador); complementa 0039 e 0030 |
| [0041](0041-eleito-completo-e-fim-das-views-app.md) | `fl_eleito` passa a ser o eleito completo (informado ou derivado) e as views `app_*` deixam de existir | aceito; altera 0039 (item sobre `fl_eleito`) e 0038 (item 4) |
| [0045](0045-meses-fechados-405-e-pacote-unico.md) | Meses fechados (`lag_months`), 405 como bloqueio e um download por pacote | aceito; complementa o [0038 (cortesia)](0038-cortesia-e-bloqueio-na-ingestao.md) |

### Estrutura do repositório e das camadas

| ADR | Decisão | Situação |
| --- | --- | --- |
| [0004](0004-camadas-da-plataforma-de-dados.md) | Camadas e identidade de pessoas | em parte (ideia de camadas e identidade valem; pastas e nomes: 0005 a 0007) |
| [0007](0007-dois-pacotes-e-camadas-de-mercado.md) | Camadas com nomes de mercado (dois pacotes) | em parte (nomes das camadas valem; pacotes: [0009](0009-repositorio-de-dados-pacote-unico.md)) |
| [0008](0008-motores-separados-e-organizacao-por-poder-e-esfera.md) | Motores separados; poder, esfera e fonte | em parte (organização por poder/esfera/fonte vale; pacotes: 0009) |
| [0009](0009-repositorio-de-dados-pacote-unico.md) | Um só pacote Python, motores como subpacotes | vigente |
| [0010](0010-duas-pastas-env-e-specs-fora.md) | `.env` para conexões; duas pastas | em parte (repositório próprio: [0020](0020-repositorio-proprio-dado-publico-brasil.md)) |
| [0020](0020-repositorio-proprio-dado-publico-brasil.md) | Repositório próprio `dado-publico-brasil` | vigente |

### Captura e landing

| ADR | Decisão | Situação |
| --- | --- | --- |
| [0005](0005-fontes-declarativas-e-portabilidade.md) | Fontes declarativas e configuração central | em parte (declaração vale; motor próprio: 0006) |
| [0011](0011-buscar-ler-custom-e-chave-por-fonte.md) | Buscar, ler e código próprio por fonte | vigente |
| [0012](0012-dataset-por-item-lotes-com-envelope.md) | Dataset por item, lotes com envelope | vigente |
| [0019](0019-dou-so-no-landing.md) | Diário Oficial só no landing | vigente |
| [0021](0021-landing-por-fonte-dataset-e-data.md) | Landing por fonte, dataset, referência e data | vigente |
| [0024](0024-regras-de-extracao-por-fonte.md) | Regras de extração e carga diária | em parte (`refresh` virou `schedule`: [0027](0027-orquestracao-automatica-por-fonte.md)) |
| [0027](0027-orquestracao-automatica-por-fonte.md) | Agendamento por fonte, propagação automática e serviço contínuo | em parte (propagação por evento: [0042](0042-ciclo-noturno-de-processamento-e-publicacao.md), proposto) |
| [0042](0042-ciclo-noturno-de-processamento-e-publicacao.md) | Ciclo noturno: capturas escalonadas, um processamento e uma publicação por dia | proposto |
| [0043](0043-raw-em-parquet-substituicao-por-particao-e-logs.md) | Raw carregado em Parquet (`pyarrow`), `write: replace_partition` para arquivo anual completo e logs no Dagster | proposto; altera 0011, 0012 e 0024 |
| [0044](0044-ciclo-rapido-staging-do-tse-em-tabela-e-tempos.md) | Ciclo mais rápido: staging do TSE em tabela, tempo de cada nó; propostas de `threads` e de reconstrução parcial | proposto; altera o 0007 (item 3: staging = views)

### Nomes, qualidade e dados pessoais

| ADR | Decisão | Situação |
| --- | --- | --- |
| [0017](0017-revisao-de-filtros-e-dados-pessoais.md) | Filtros, chaves e dados pessoais | vigente |
| [0018](0018-observabilidade-dos-dados.md) | Observabilidade com Elementary e relatório | vigente |
| [0022](0022-convencao-de-nomes-e-descricoes.md) | Convenção de nomes e descrições | vigente |

### Fontes e pessoas

| ADR | Decisão | Situação |
| --- | --- | --- |
| [0013](0013-tse-ligacao-por-nome-civil-e-nascimento.md) | TSE e ligação por nome civil e nascimento | em parte (itens 2 e 6: [0029](0029-campos-de-pessoas-nos-marts.md)) |
| [0015](0015-normas-vetos-e-constituicao.md) | Normas, vetos e Constituição | vigente |
| [0016](0016-bens-votos-e-emendas.md) | Bens, votos por candidato e emendas | vigente |
| [0023](0023-eleitos-escopo-regras-e-fontes.md) | Eleitos: escopo, regras e fontes | substituído em parte por [0030](0030-modelo-de-dados-pessoa-no-centro.md) (marts `eleitos*` aposentados) |
| [0025](0025-historico-do-eleito-ligacao-entre-eleicoes-do-tse.md) | Histórico do eleito entre eleições | proposto (aprovado pelo fundador) |
| [0026](0026-segunda-chave-nome-de-urna-e-nascimento.md) | Segunda chave: nome de urna e nascimento | proposto (aprovado pelo fundador) |
| [0028](0028-ligar-vetos-e-emendas-a-pessoas.md) | Ligar votos de vetos e emendas a pessoas | proposto |
| [0029](0029-campos-de-pessoas-nos-marts.md) | Campos de pessoas no raw e nos marts | proposto (aprovado pelo fundador) |
| [0030](0030-modelo-de-dados-pessoa-no-centro.md) | Modelo de dados com a pessoa no centro, eventos tipados e composições | proposto (aprovado pelo fundador); altera 0023 em fases; a organização em esquemas foi substituída pelo [0033](0033-marts-com-a-terminologia-da-dbt-labs.md) |
| [0031](0031-pessoas-de-todo-eleito.md) | Pessoas de todo eleito, ancoradas na candidatura (F3 do 0030) | proposto (aprovado pelo fundador); altera 0004 e 0013 |
| [0032](0032-partido-da-pessoa-por-fonte-e-filiacao.md) | O partido da pessoa vem de fontes oficiais (candidatura, histórico da Câmara, votos); a filiação por data fica de fora | proposto (decisão do fundador); altera o item 10 do 0030 |
| [0033](0033-marts-com-a-terminologia-da-dbt-labs.md) | Uma só camada publicada, `marts`, com a terminologia da dbt Labs (`dim_`, `fct_`, `brg_`, `agg_`, `app_`) | proposto (decisão do fundador); altera a organização em esquemas do 0030 e o 0007; item 2 alterado pelo [0038](0038-lake-como-unica-publicacao.md) |

Ao criar um ADR, acrescente uma linha aqui e, se ele substituir outro, atualize a situação do antigo.
