# Decisões de arquitetura (ADRs)

Para quem quer saber **por que** algo é como é. Responde: quando uma decisão vira ADR, como ler um, quais valem hoje e onde achar cada assunto. O resumo do que vale hoje está em [`../01-entender/02-arquitetura.md`](../01-entender/02-arquitetura.md); o ADR traz o contexto e as alternativas.

## Quando vira ADR e como é escrito

- Vira ADR a decisão que **fixa ou muda a arquitetura, uma ferramenta, uma regra de dados ou a estrutura** do repositório, e que seria cara de desfazer. Dependência nova exige ADR. Correção de bug e ajuste de código não.
- Um arquivo por decisão, numerado em ordem: `NNNN-assunto.md`. Formato: Status, Data, (Substitui/Altera), **Contexto**, **Decisão**, **Alternativas consideradas**, **Consequências**.
- **Uma decisão aceita não é editada.** Se mudar, nasce um ADR novo que diz o que substitui ou altera; o antigo continua como registro, e a tabela abaixo mostra qual vale.
- Quem propõe é a pessoa ou o agente; quem aceita é o fundador.

## Situação e índice por assunto

**Vigente:** vale como escrito. **Em parte:** só o que o ADR seguinte não substituiu. **Proposto:** ainda não aceito.

### Processo e pilha

| ADR | Decisão | Situação |
| --- | --- | --- |
| [0001](0001-fases-e-portoes.md) | Trabalhar em fases com portões verificáveis | proposto |
| [0002](0002-pilha-tecnologica.md) | Pilha tecnológica do piloto | em parte (dados curados: [0014](0014-warehouse-lake-duckdb-e-postgres-de-servico.md)) |
| [0003](0003-ferramentas-de-seguranca-do-ci.md) | Ferramentas de segurança do CI | proposto |
| [0006](0006-adotar-dlt-dbt-e-dagster.md) | Adotar dlt, dbt-core e Dagster | vigente (pastas e nomes: [0007](0007-dois-pacotes-e-camadas-de-mercado.md)) |
| [0014](0014-warehouse-lake-duckdb-e-postgres-de-servico.md) | DuckDB calcula, PostgreSQL serve | vigente |

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
| [0027](0027-orquestracao-automatica-por-fonte.md) | Agendamento por fonte, propagação automática e serviço contínuo | vigente |

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
| [0023](0023-eleitos-escopo-regras-e-fontes.md) | Eleitos: escopo, regras e fontes | vigente (será substituído em fases: [0030](0030-modelo-de-dados-pessoa-no-centro.md)) |
| [0025](0025-historico-do-eleito-ligacao-entre-eleicoes-do-tse.md) | Histórico do eleito entre eleições | proposto (aprovado pelo fundador) |
| [0026](0026-segunda-chave-nome-de-urna-e-nascimento.md) | Segunda chave: nome de urna e nascimento | proposto (aprovado pelo fundador) |
| [0028](0028-ligar-vetos-e-emendas-a-pessoas.md) | Ligar votos de vetos e emendas a pessoas | proposto |
| [0029](0029-campos-de-pessoas-nos-marts.md) | Campos de pessoas no raw e nos marts | proposto (aprovado pelo fundador) |
| [0030](0030-modelo-de-dados-pessoa-no-centro.md) | Modelo de dados com a pessoa no centro, eventos tipados e composições | proposto (aprovado pelo fundador); altera 0023 em fases |
| [0031](0031-pessoas-de-todo-eleito.md) | Pessoas de todo eleito, ancoradas na candidatura (F3 do 0030) | proposto (aprovado pelo fundador); altera 0004 e 0013 |

Ao criar um ADR, acrescente uma linha aqui e, se ele substituir outro, atualize a situação do antigo.
