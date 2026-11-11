# Changelog

Para quem consome o lake ou o código e quer saber o que mudou entre versões. Segue o formato [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/) e o [versionamento semântico](https://semver.org/lang/pt-BR/), aplicado como diz a [política de estabilidade](docs/03-consultar/06-consumir-o-lake.md#estabilidade-e-versionamento). Cada item cita o PR; a lista completa está em `gh pr list --state merged`.

## [Não lançado]

## [0.1.0] - a datar na tag

Primeira versão marcada. O projeto está em desenvolvimento: a partir daqui, mudança que quebra o contrato dos marts aparece neste arquivo.

### Adicionado

- Ingestão declarativa por fonte (`sources/<poder>/<esfera>/<fonte>.yml`), landing imutável com hash e raw em Parquet: Câmara, Senado, TSE (eleições, candidaturas, prestação de contas, fotos), IBGE e Portal da Transparência (despesas, contratos e licitações) (#34, #61, #73, #89, #206, #224, #265).
- Marts com a pessoa no centro, no padrão `dim_`, `fct_`, `brg_` e `agg_`: pessoas, partidos, candidaturas, mandatos, exercícios, eventos, campanhas e ocupação de cargo, com descrição em toda tabela e coluna (#52, #122, #128, #131, #169, #211).
- Identidade de pessoas por ligação entre fontes, com vínculos revisados (#79, #133, #286).
- Lake público em Parquet no R2, com `manifesto.json`, catálogo e `metadata/capturas` para chegar à fonte de cada dado (#203, #206).
- Orquestração com Dagster (agendamento por fonte, ciclo noturno, publicação única ao fim) e `scripts/servidor.sh` para o servidor (#87, #204, #233, #230).
- Observabilidade e auditoria: frescor por dataset, saúde por dimensão de qualidade, `verify`, `coverage` e testes de dado `error` e `warn` (#142, #146, #235, #261).
- Esteira de CI com actions por hash, `gitleaks`, `uv audit`, SBOM, assinatura da imagem e Scorecard (#290, #296).
- Licença Apache-2.0 para o código e CC BY 4.0 para os dados curados, com a licença declarada por fonte (#283, #285).
- Documentação por propósito (`docs/01-entender` a `05-decisoes`), `CONTRIBUTING.md` e `SECURITY.md` (#80, #81, #83, #84).

### Alterado

- `fct_candidaturas.fl_eleito` passou a ser o eleito completo (informado ou derivado); o valor antigo ficou em `fl_eleito_informado` (#220, #223).
- O lake é a única publicação: o PostgreSQL de serviço e as views `app_*` foram removidos (#207, #223).
- Raw em Parquet com substituição por partição, recarga por mudança de chave e reconstrução seletiva do dbt com export por partição (#234, #240, #242, #287).
- Marts renomeados pela convenção de nomes e pela terminologia da dbt Labs (#52, #169).

### Corrigido

- Download retoma com `Range` e só registra captura inteira (#258).
- TSE: sem a máscara parcial de conta bancária em bens e despesas e sem os marcadores `#NE` e `#NULO` no staging (#291, #145).
- Votações do Senado com data errada na fonte não criam mandato (#107).

### Segurança

- Documentos pessoais (CPF, RG) não entram em nenhuma camada; canal privado para vulnerabilidade e pedido de titular em [`SECURITY.md`](SECURITY.md) (#83, #203).

[Não lançado]: https://github.com/codigo-publico-brasil/dado-publico-brasil/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/codigo-publico-brasil/dado-publico-brasil/releases/tag/v0.1.0
