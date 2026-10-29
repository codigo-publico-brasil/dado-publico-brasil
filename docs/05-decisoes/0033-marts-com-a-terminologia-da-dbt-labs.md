# ADR 0033: uma só camada publicada, `marts`, com a terminologia da dbt Labs

- **Status:** proposto (2026-10-29); decisão do fundador na conversa de 29/10/2026
- **Data:** 2026-10-29
- **Altera:** a organização em esquemas do [ADR 0030](0030-modelo-de-dados-pessoa-no-centro.md) (`core`, `fatos`, `analise` e `servico` deixam de existir; o conteúdo e as regras de pessoa, evento e composição seguem valendo), o [ADR 0007](0007-dois-pacotes-e-camadas-de-mercado.md) e o que o Postgres de serviço recebe ([ADR 0014](0014-warehouse-lake-duckdb-e-postgres-de-servico.md)).

Para quem mantém os modelos: responde que camadas existem depois do `intermediate`, como nomear as tabelas e por que seguimos o vocabulário do mercado.

## Contexto

Depois do `intermediate` conviviam cinco esquemas (`core`, `fatos`, `analise`, `servico` e os `marts` antigos). Dois deles se diziam "o que o aplicativo lê", o `servico` lia dos marts, e os 39 marts antigos tinham nascido por pergunta (`eleitos`, `eleitos_campanhas`), com grãos repetidos. Os nomes `core`, `fatos` e `servico` eram nossos: quem chega ao projeto conhece `staging`, `intermediate` e `marts` do guia da dbt Labs e as dimensões e fatos de Kimball, e inventar vocabulário só atrapalha. (Medido em 29/10/2026: o site ainda lê `marts.*`.)

## Decisão

1. **Três camadas do dbt, como no guia da dbt Labs:** `staging` (`stg_`), `intermediate` (`int_`) e `marts`. Acabam `core`, `fatos`, `analise` e `servico`.
2. **`marts` é a única camada publicada** no Postgres e o único contrato com os aplicativos. Tudo com contrato de colunas e descrição.
3. **O prefixo diz o tipo da tabela:** `dim_` (dimensão; se guarda a história por período, é SCD tipo 2 com `dt_inicio`, `dt_fim` e `fl_vigente`, sem prefixo extra), `fct_` (fato), `brg_` (ponte muitos-para-muitos), `agg_` (agregado por período) e `app_` (consulta pronta do aplicativo, larga e sem regra de negócio, pode ser view). `snp_` fica reservado para snapshots do dbt. Detalhe em [`02-convencao-de-nomes.md`](../03-consultar/02-convencao-de-nomes.md).
4. **Pastas por assunto** dentro de `marts/` (`pessoas`, `eleicoes`, `legislativo`, `territorio`, `aplicacao`), como a dbt Labs faz por área.
5. **Os marts antigos saem.** Os que eram entidades passam a `dim_`, `fct_` ou `brg_`; os que repetiam outro modelo ou nasceram por pergunta foram removidos (`eleitos*`, `candidaturas`, `mandatos`, `mandatos_exercicios`, `orgaos` e `votacoes_votos`, esta substituída por `fct_votos`).
6. **Sem views de compatibilidade.** Quem lê o Postgres migra para os nomes novos.

## Alternativas

- **Manter `core`, `fatos`, `analise` e `servico`:** é o desenho do ADR 0030, mas é vocabulário próprio e deixava dois contratos.
- **Manter `marts` e `servico` com papéis separados:** menos trabalho agora, mas a dependência `servico → marts` e a pergunta "onde entra este modelo?" ficavam.

## Consequências

- Um vocabulário só, que o mercado reconhece, e uma camada publicada.
- O site e outros consumidores precisam migrar para os nomes novos. O Postgres antigo terá os esquemas `servico` e os marts antigos até o próximo `publish`; o `servico` precisa ser removido à mão.
- O código e a documentação que citavam `fatos.x`, `core.x` ou `servico.x` foram atualizados; ADRs aceitos não foram reescritos, e a leitura deles deve usar a tabela de correspondência do 0033 (`core` → `dim_`, `fatos` → `fct_`, `analise` → `agg_`, `servico` → `app_`).
- Merece ADR próprio, se aparecer: a política de retenção e a linhagem por linha (issue #163).
