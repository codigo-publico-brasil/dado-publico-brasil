# ADR 0008: Motores de ingestão e de transformação separados; organização por poder, esfera e fonte

- **Status:** aceito (2026-10-21, pelo fundador)
- **Data:** 2026-10-21
- **Substitui em parte:** [ADR 0007](0007-dois-pacotes-e-camadas-de-mercado.md) (o pacote único `data-platform` vira quatro). Mantém dele: camadas com nomes de mercado, dbt pelo guia da dbt Labs, aplicação separada da camada de dados.
- **Depende de:** [ADR 0006](0006-adotar-dlt-dbt-e-dagster.md) (dlt, dbt-core, Dagster)

## Contexto

O projeto vai capturar dados dos três poderes (legislativo, executivo, judiciário) e das três esferas (federal, estadual, municipal), começando pelo legislativo federal. Algumas fontes serão APIs, outras arquivos, outras talvez robôs (RPA) ou raspagem. Duas necessidades pediram uma estrutura melhor:

1. **Manutenção.** Ingestão e transformação evoluem por motivos diferentes (a fonte muda; a regra de negócio muda) e estavam no mesmo pacote, ligadas pelo `pipeline.py` e por um `core/` que misturava as duas.
2. **Escala de fontes.** Com dezenas de fontes, schemas, pastas e tabelas precisam seguir uma regra previsível, e é preciso saber logo quando uma fonte quebra ou muda de formato.

## Decisão

### 1. Cinco pacotes com dependências em uma direção

```text
packages/
  core/            quem_decidiu_core            configuração, warehouse, execuções, migrações
  ingestion/       quem_decidiu_ingestion       captura (landing), carga no raw (dlt), monitoramento
  transformation/  quem_decidiu_transformation  projeto dbt, identidade de pessoas, qualidade, catálogo
  orchestration/   quem_decidiu_orchestration   liga os dois motores: linha de comando e Dagster
  app/             quem_decidiu_app             consumo; lê só os marts
```

| Pacote | Pode importar |
| --- | --- |
| `core` | nenhum |
| `ingestion` | `core` |
| `transformation` | `core` |
| `orchestration` | `core`, `ingestion`, `transformation` |
| `app` | nenhum |

**A fronteira entre os motores é de dados, não de código:** o schema `raw_<esfera>_<fonte>` e a tabela `metadata.captures`. Um teste confere a matriz acima. Trocar a forma de captura (API por RPA) só mexe na ingestão; uma regra nova de negócio só mexe na transformação.

### 2. Poder, esfera e fonte

- **Declaração da fonte:** `ingestion/.../sources/<poder>/<esfera>/<fonte>.yml`, por exemplo `sources/legislativo/federal/camara.yml`. O arquivo declara `source`, `power` e `level`, e a pasta repete os dois, para que a árvore seja a documentação.
- **Schema do raw:** `raw_<esfera>_<fonte>` (por exemplo `raw_federal_camara`, `raw_municipal_saopaulo`). O poder não entra no nome do schema para não alongá-lo; ele fica na declaração e no catálogo.
- **Camadas seguintes:** `staging` (um modelo por tabela do raw, `stg_<fonte>__<entidade>`), `intermediate` e `marts` continuam sem prefixo de fonte. Os marts são **por entidade** (`pessoas`, `proposicoes`, `votacoes`, `votos`) e cada linha leva a coluna `fonte`, para que Câmara e Senado possam ser consultados juntos. As colunas `poder` e `esfera` entram nos marts quando a primeira fonte de outro poder ou esfera chegar; hoje seriam constantes.
- **Pasta chamada `contracts/`** passa a se chamar `sources/` para não ser confundida com os contratos de dados do dbt nem com os documentos de design em `specs/*/contracts/`.

### 3. Captura flexível: adaptadores por tipo de acesso

A declaração da fonte diz **como** capturar (`access`), e a captura é a única parte que conhece o tipo de acesso:

| Tipo de acesso | Situação |
| --- | --- |
| `file` (CSV/arquivo por URL) | implementado |
| `rest` (API JSON por janela) | a implementar com o Senado |
| `soap`, `rpa` (robô ou raspagem) | previstos; um robô só precisa **gravar o arquivo obtido no landing**, com URL e data, e registrar a captura |

Depois do landing, todo o resto (carga no raw, staging, marts) é igual para qualquer tipo de acesso. O que o adaptador entrega é sempre um arquivo com hash, e `metadata.captures` registra de onde veio.

### 4. Monitoramento das fontes

Cada captura grava verificações em `metadata.source_checks` (`ok`, `warn`, `error`):

| Verificação | O que detecta |
| --- | --- |
| `availability` | a fonte não respondeu (HTTP, rede); o plano segue e a falha é registrada |
| `schema` | coluna do contrato ausente no arquivo (erro) e colunas novas ou removidas em relação ao arquivo anterior (aviso) |
| `volume` | carga com menos de 80% das linhas da anterior para o mesmo dataset e partição |
| frescor | idade do dado carregado, medida pelo dbt (`freshness`) |

Nada disso interrompe o pipeline: o objetivo é saber que algo quebrou sem parar o que ainda funciona. A execução devolve a contagem de erros da execução (`source_errors`). Alertas por e-mail ou mensagem ficam para depois; o registro em tabela é a base.

## Alternativas consideradas

- **Manter o pacote único com subpacotes.** Menos arquivos de configuração, mas o isolamento dependeria de disciplina. Os cinco pacotes permitem separar repositórios e dão um teste simples de fronteira.
- **Schema por poder e esfera (`legislativo_federal.camara_votos`).** Agrupa melhor, mas multiplica schemas e quebra a convenção do dlt de um schema por fonte.
- **Marts por fonte (`marts_senado`).** Impediria a consulta conjunta, que é o objetivo do projeto.
- **Ferramenta de observabilidade de dados externa.** Seria mais completa, mas é dependência nova; três verificações em uma tabela cobrem o necessário agora.

## Consequências

- O raw foi recarregado no schema novo (`raw_federal_camara`) a partir do landing, sem baixar nada de novo; o schema antigo foi removido.
- O comando passa a ser `python -m quem_decidiu_orchestration` (antes `quem_decidiu_data`).
- O catálogo agrupa os schemas `raw_*` na primeira camada.
- Risco aceito: mais pacotes para manter versões coerentes; o workspace uv os instala juntos.
