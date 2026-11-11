# Governança do projeto

Para quem quer saber quem decide o quê neste repositório e como propor mudança. Não confundir com a governança dos dados ([`docs/01-entender/06-governanca.md`](docs/01-entender/06-governanca.md)).

## Quem decide

O projeto tem um fundador, que é o único mantenedor: decide o rumo, aprova ADRs e faz o merge ([`CODEOWNERS`](.github/CODEOWNERS)). Não há comitê, empresa ou fundação por trás; se isso mudar, este arquivo muda antes. Agentes de IA escrevem e revisam código, mas nunca decidem nem fazem merge ([`AGENTS.md`](AGENTS.md)).

## Como entra uma decisão (ADR)

Mudança de arquitetura, estrutura, ferramenta ou dependência nova pede um ADR em [`docs/05-decisoes/`](docs/05-decisoes/README.md):

1. Abra uma issue ou PR com contexto, decisão e alternativas, com status **proposto**.
2. O fundador aceita, pede ajuste ou recusa, e a situação muda no índice.
3. Decisão aceita não se edita: um ADR novo a substitui, e o antigo muda de situação.

## Como se revisa um PR

Um assunto por PR, checks verdes ([`CONTRIBUTING.md`](CONTRIBUTING.md)), documentação no mesmo PR e seção "autoria da IA" preenchida. O fundador revisa e faz o merge. As regras de dados do [`README.md`](README.md) não se negociam.

## Versões

O fundador marca a tag e escreve o [`CHANGELOG.md`](CHANGELOG.md), pela [política de estabilidade](docs/03-consultar/06-consumir-o-lake.md#estabilidade-e-versionamento).

## Conduta e segurança

[`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md) e [`SECURITY.md`](SECURITY.md).
