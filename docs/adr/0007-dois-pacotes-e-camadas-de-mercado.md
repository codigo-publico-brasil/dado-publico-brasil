# ADR 0007: Dois pacotes (dados e aplicação) e camadas com nomes de mercado

- **Status:** aceito (2026-10-20, pelo fundador)
- **Data:** 2026-10-20
- **Substitui em parte:** [ADR 0004](0004-camadas-da-plataforma-de-dados.md) (nomes das camadas e estrutura de pastas), [ADR 0005](0005-fontes-declarativas-e-portabilidade.md) (onde ficam as declarações) e [ADR 0006](0006-adotar-dlt-dbt-e-dagster.md) (onde a limpeza de texto acontece). Mantém deles: dlt, dbt-core, Dagster e DuckDB; a identidade de pessoas como código próprio; a regra conservadora de ligação.

## Contexto

A primeira implementação funcionava, mas a estrutura estava confusa: código dentro e fora de `src/`, uma pasta de "ganchos" para o que a configuração não cobria, a limpeza de texto escrita em Python dentro do carregador, regras repetidas em testes do dbt e em verificações em Python, e nomes que não são os de mercado (bruto, padronizado, integrado, servico). Também não havia separação real entre a camada de dados e a camada de aplicação. O fundador pediu: separar as duas camadas de verdade, seguir exatamente as práticas do dbt e usar a terminologia da área.

## Decisão

### 1. Dois pacotes independentes (workspace uv)

```text
packages/data-platform/   pacote quem_decidiu_data   camada de dados
packages/app/             pacote quem_decidiu_app    camada de aplicação
src/quem_decidiu/         raiz do workspace: versão e ferramentas de desenvolvimento (feature 001)
```

A aplicação **não importa** a camada de dados. O contrato entre as duas é o esquema `marts` do warehouse (colunas e tipos garantidos por `contract.enforced` do dbt), mais `metadata.captures` e `metadata.dbt_results`, usados na página de qualidade. Testes verificam a ausência de imports nos dois sentidos. Se os pacotes virarem repositórios separados, basta mover a pasta.

### 2. Camadas com nomes de mercado

| Antes | Agora | Quem produz |
| --- | --- | --- |
| bruto (arquivos) | `landing` | código próprio (hash, captura, pergunta condicional à fonte) |
| padronizado | `raw_<fonte>` (tabelas fiéis à fonte) | dlt, guiado por `contracts/<fonte>.yml` |
| padronizado limpo | `staging` | dbt, views, um modelo por tabela do raw |
| integrado | `intermediate` | dbt, tabelas, uma finalidade por modelo |
| servico | `marts` | dbt, tabelas, entidades com contrato |
| controle | `metadata` | código próprio e dbt |
| identidade | `identity` | código próprio |

Termos técnicos em inglês; entidades do domínio em português (`pessoas`, `proposicoes`, `votos`), porque são os termos oficiais da legislação.

### 3. dbt seguindo o guia da dbt Labs

- `staging`: `stg_<fonte>__<entidades>`, 1:1 com o raw, renomear, converter tipos e padronizar texto, sem joins nem agregações; único lugar que usa `source()`.
- `intermediate`: re-granularidade e joins, uma finalidade por modelo.
- `marts`: entidades no plural, um grain por tabela, largas, com contrato, declaradas como *exposure* para a aplicação. Sem prefixos `fct_` e `dim_`, como no guia atual.
- YAML ao lado dos modelos, com descrição, `meta` e testes; `freshness` nas fontes.
- Testes genéricos mais singulares; lacunas conhecidas como `warn`, reconciliações e integridade como `error`.
- Funções de texto como macros nativas do DuckDB (`on-run-start`), sem código Python por linha.
- Catálogo de dados gerado do manifesto do dbt.

### 4. O raw é fiel; o carregador é fino

O dlt carrega só as colunas permitidas pelo contrato, como texto, sem renomear nem limpar. Saem do código: a linguagem de regras (`regra:`), a deduplicação, as tabelas derivadas (partido, órgão), os ganchos e a lista de siglas por arquivo. Tudo isso passou para SQL de staging, intermediate e marts.

### 5. Duas fases do dbt e a identidade no meio

A chave própria de pessoa é código Python e depende de modelos do dbt (a lista de deputados vistos) e alimenta outros. O pipeline roda o dbt em duas passadas por tag (`pre_identity`), com seleção indireta `cautious` para que um teste só rode quando todos os modelos de que depende existem.

## Alternativas consideradas

- **Pacote único com subpacotes:** mais simples, mas não deixa a separação em repositórios barata.
- **Python UDF no DuckDB para as regras de texto:** exigiria `numpy` (dependência nova) e processa linha a linha; macros SQL foram suficientes e seguem o estilo dbt.
- **Manter os nomes em português:** coerente com o domínio, mas fora do vocabulário que o mercado usa para as camadas.

## Consequências

- Muitos arquivos mudam de lugar e de nome; a carga real foi refeita e comparada com a anterior.
- O contrato de colunas dos marts torna mudança incompatível um erro de build, não um dado quebrado na aplicação.
- Mais um conceito para quem chega (duas fases do dbt), compensado pela documentação em `docs/dados/camadas.md`.
- Limites conhecidos: DuckDB em arquivo aceita um escritor por vez; o caminho do PostgreSQL não foi exercitado; a interface do Dagster não foi aberta (as definições carregam e a linhagem foi validada em teste).
