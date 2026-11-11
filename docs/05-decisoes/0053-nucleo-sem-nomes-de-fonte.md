# ADR 0053: Núcleo sem nomes de fonte

- **Status:** proposto
- **Data:** 2026-11-11
- **Complementa:** o [ADR 0011](0011-buscar-ler-custom-e-chave-por-fonte.md) (o que é próprio da fonte mora na declaração ou em `custom/`) e o [ADR 0051](0051-raw-em-parquet-por-captura-e-estado-em-arquivo-proprio.md) (`metadata` e `identity` em `estado.duckdb`, que não se reconstroem).
- **Para quem é:** quem implementa ou revisa o núcleo. Responde: onde o núcleo ainda nomeia fonte, para onde cada ponto vai, em que ordem e como se prova que nada mudou.
- **Origem:** Refs #275 (diagnóstico, itens A4 e A6).

## Contexto

O `AGENTS.md` diz que o núcleo (`core`, CLI, orquestração, `ingestion` fora de `custom/`, `transformation`) não nomeia fonte: fonte nova entra só com YAML. A busca no código (2026-11-11) achou três pontos que violam isso e um que procura dado em texto livre:

| # | Onde | O que o código decide |
| --- | --- | --- |
| A | `ingestion/landing.py:149-151` (`legislature_of`: `56 + (ano - 2019) // 4`), `:162`, `:181-182`; `ingestion/contract.py:150-155` (`{legislature}` na URL) | o calendário da legislatura federal, usado por um dataset da Câmara e um do Senado. Uma assembleia estadual ou câmara municipal com outra numeração exigiria mudar o núcleo |
| B | `transformation/identity.py:25` (`int_tse_eleitos_grupos`), `:28-29`, `:102`, `:114-134`, `:163-197` (`'tse'`, `fonte IN ('camara', 'senado')`, `_tse_people`) | quais fontes são cadastro oficial (sobrevivem na fusão e nunca se fundem entre si) e qual tem vínculos derivados, recalculados a cada execução |
| C | `ingestion/landing.py:291-293` (`"404" in detalhe or "ainda não publicado" in detalhe`); `dbt/tests/reconciliation/carga_do_raw_diferente_da_captura.sql:16` (`regexp_extract(detalhe, 'carregadas ([0-9]+)')`) | o código HTTP, o tipo da ocorrência e as contagens vivem dentro de `metadata.fontes_verificacoes.detalhe`; mudar a redação da mensagem quebra, em silêncio, a detecção de partição indisponível e a reconciliação da carga |

Fora do escopo, por não nomearem fonte: `dim_pessoas` em `transformation/build.py:127` e `int_pessoas_ids_vistos` em `orchestration/definitions.py:123` (a pessoa é entidade da plataforma, ADR 0004); `zip`, `csv` e `json` em `contract.py`/`read.py` (capacidades que o YAML escolhe); `POWERS` e `LEVELS` (taxonomia de `sources/`). Comentários que citam uma fonte como exemplo (`fetch.py:64,114`, `__main__.py:8,68`, `landing.py:316`, `read.py:71`) saem no PR da trava.

## Decisão

1. **Partição por sequência declarada (A).** O tipo `legislature` dá lugar a `partition: sequence`, com a âncora e o passo no YAML do dataset:

   ```yaml
   partition: sequence
   sequence: {first_year: 2019, first_value: 56, years: 4}   # legislatura federal
   ```

   O núcleo calcula `first_value + (ano - first_year) // years`, sem saber o que o número significa. A URL passa a usar `{partition}`, aceito em todo tipo de partição; `{year}` e `{month}` continuam. **O valor da partição não muda**, então o caminho do landing e a URL ficam idênticos (o landing é imutável).
2. **Papel das fontes na identidade em seed (B).** `dbt/seeds/intermediate/fontes_identidade.csv`, com `fonte`, `precedencia` (menor vence; o cadastro oficial é 1) e `fl_vinculo_derivado`, descrita no YAML ao lado. O modelo de grupos vira genérico (`int_pessoas_grupos`, com `fonte`, `id_tipo`, `id_na_fonte`, `grupo` e `metodo`), e o `identity.py` lê só a seed e esse modelo. A seed é o lugar certo e não o YAML de uma fonte porque a regra é uma **relação entre fontes**; e já é o padrão para dado curado que alimenta o dbt ([seeds](https://docs.getdbt.com/docs/build/seeds), como `vinculos_aprovados`). Os valores gravados em `identity` (`fonte`, `id_tipo`, `metodo`) ficam **byte a byte iguais**: saem do código para o modelo, não mudam.
3. **Verificações com colunas próprias (C).** Migração aditiva em `ddl/` acrescenta a `metadata.fontes_verificacoes`: `cd_status_http` (código da resposta), `tipo_ocorrencia` (`nao_encontrado`, `nao_publicado`, `bloqueio`...), `qtd_bytes_esperados`, `qtd_bytes_recebidos` e `qtd_linhas`. Quem grava preenche as colunas; quem lê consulta por elas. `detalhe` continua como texto para gente. As linhas antigas são preenchidas na própria migração, por extração determinística do `detalhe` (que fica, para auditoria); o que não casa fica vazio. Pré-requisito do mart de ocorrências das fontes.
4. **Trava por teste.** `tests/` ganha um teste que lê os nomes das fontes de `sources/**/*.yml` (sem lista própria) e reprova literal de texto ou identificador do Python do núcleo que os contenha (análise por `ast`, para não pegar comentário legítimo). Nasce com a lista das exceções de hoje, e cada PR abaixo esvazia uma parte; o último a deixa vazia.

### Plano de PRs (um por ponto, do menor risco ao maior)

| PR | Conteúdo | Prova |
| --- | --- | --- |
| 1 | trava (item 4) com as exceções atuais; limpeza dos comentários | o teste passa com a lista e reprova se um nome novo entrar |
| 2 | partição por sequência (item 1); YAML da Câmara e do Senado e cabeçalho de `camara.yml` | para todo ano de 1990 a 2040 e para os dois datasets: `partitions`, `current_partition`, URL e caminho do landing iguais aos de `main` |
| 3 | verificações com colunas (item 3), no código e no teste de reconciliação | numa cópia do `estado.duckdb` real: contagem por `verificacao` e `resultado` igual antes e depois; conjunto de partições indisponíveis e resultado da reconciliação iguais aos da busca em texto |
| 4 | identidade por seed (item 2) | no pipeline sintético, soma de hash de `identity.pessoas`, `pessoas_identificadores` e `pessoas_fusoes` e o `id_pessoa` de `dim_pessoas` iguais aos de `main`; numa cópia do `estado.duckdb` real, rodar `identity` duas vezes não muda nenhuma linha |

## Alternativas consideradas

- **Deixar como está:** custo zero agora. Mas a próxima casa legislativa com outra numeração, ou uma fonte nova de identidade, obriga a mexer no núcleo; e a busca em texto falha sem erro (uma partição indisponível passa a aparecer como faltante, e a reconciliação compara com vazio). Descartada: os três pontos são dado, não comportamento.
- **Registro de plugins** (funções por fonte registradas no núcleo, ou [entry points](https://packaging.python.org/en/latest/specifications/entry-points/)): flexível, mas é estrutura para três casos que cabem em dados (uma fórmula com três números, uma tabela de duas colunas, colunas de uma tabela). O ponto de extensão por código já existe: `custom/` (ADR 0011). Descartada; reabre se aparecer comportamento por fonte que nem YAML nem `custom/` cubram.
- **Precedência no YAML de cada fonte** (`identity: {precedencia: 1}`): mantém tudo da fonte num arquivo, mas espalha uma regra entre fontes por vários arquivos e o dbt também precisa dela. A seed é lida pelo dbt e pelo Python.

## Consequências

- Fonte nova com calendário próprio, ou que entre na identidade, não toca o núcleo: YAML, seed e modelo dbt.
- Mudança de contrato: `partition: legislature` e `{legislature}` deixam de ser aceitos (a validação diz o novo formato). A âncora da legislatura federal fica repetida em dois YAMLs; aceitável por serem duas linhas.
- `metadata` e `identity` não se reconstroem (ADR 0036): os PRs 3 e 4 se provam numa cópia, e a migração é aditiva (nenhuma coluna sai). Cópia de segurança do `estado.duckdb` antes de implantar.
- O teste de nomes e descrições passa a cobrir as colunas novas e a seed (convenção em `docs/03-consultar/02-convencao-de-nomes.md`; nenhum prefixo novo).
- Documentação no mesmo PR de cada ponto: o cabeçalho dos YAMLs, `docs/03-consultar/` (verificações) e `docs/01-entender/` (identidade).
