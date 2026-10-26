# ADR 0005: Fontes declarativas, configuração central e portabilidade do banco

- **Status:** aceito (2026-10-20, pelo fundador). Substituído em parte pelos [ADR 0006](0006-adotar-dlt-dbt-e-dagster.md) e [ADR 0007](0007-dois-pacotes-e-camadas-de-mercado.md): o motor próprio de carga, a camada sobre SQLAlchemy e o SQL executado por código próprio deram lugar a dlt, dbt e Dagster. Valem: o YAML por fonte, a configuração central, a extração histórica e incremental e a separação entre declaração e código.
- **Data:** 2026-10-20
- **Depende de:** [ADR 0002](0002-pilha-tecnologica.md) (PostgreSQL, Dagster, dbt-core) e [ADR 0004](0004-camadas-da-plataforma-de-dados.md) (camadas)

## Contexto

A primeira versão das camadas (ADR 0004) funciona, mas o conhecimento de cada fonte está espalhado em código Python e SQL escrito à mão:

- a URL da fonte está em `conjuntos.py`; a pasta de dados é um argumento de linha de comando repetido em dois programas;
- cada coluna aparece em quatro lugares (DDL, lista de colunas do `INSERT`, função de leitura do CSV e catálogo);
- acrescentar ou remover uma coluna exige editar todos eles;
- o código fala `sqlite3` diretamente (conexão, `ATTACH`, `PRAGMA`, `executescript`), então trocar de banco exige reescrever;
- a padronização mistura leitura do arquivo, regra de limpeza e gravação na mesma função;
- só existe carga completa: toda execução baixa todos os arquivos de novo.

O objetivo do projeto inclui ser material de estudo de arquitetura de dados; por isso a solução deve seguir o padrão do mercado: **o que muda com a fonte vira configuração; o que é regra de negócio vira código pequeno e testado**.

## Decisão

### 1. Uma especificação YAML por fonte

Cada fonte tem `fontes/<fonte>/fonte.yml`. Ele diz **o quê**; um motor genérico, igual para todas as fontes, faz o **como**. Código específico da fonte só existe para o que não cabe na especificação (ganchos nomeados no YAML).

```yaml
fonte: camara
descricao: Dados abertos da Câmara dos Deputados
acesso:
  url_base: https://dadosabertos.camara.leg.br/arquivos
  formato: csv          # delimitador, codificação e aspas ficam aqui
  delimitador: ";"
  codificacao: utf-8-sig
conjuntos:
  proposicoes:
    url: "{url_base}/proposicoes/csv/proposicoes-{ano}.csv"
    carga: anual                      # completa | anual
    estavel_apos_anos: 1              # anos antigos não mudam: não se baixam de novo
    tabela: camara_proposicao
    chave: [id]
    colunas:
      id:               {origem: id, tipo: inteiro}
      sigla_tipo:       {origem: siglaTipo, tipo: texto, obrigatoria: true}
      ementa:           {origem: ementa, tipo: texto}
      ementa_padronizada: {origem: ementa, tipo: texto, regra: ementa}
      situacao:         {origem: ultimoStatus_descricaoSituacao, tipo: texto, regra: rotulo}
      data_apresentacao: {origem: dataApresentacao, tipo: data_hora}
    nunca_ler: [cpf]                  # documento pessoal: o motor recusa se mapeado
    indices: [[ano]]
```

Dessa especificação saem, sem código à mão: a leitura do arquivo, a conversão de tipos, as regras de limpeza (`regra:` aponta para um registro de funções testadas: `nome_proprio`, `rotulo`, `ementa`, `id_da_uri`), o DDL da tabela, o upsert pela chave, o catálogo de dados e a lista de colunas dos testes.

**Acrescentar uma coluna** é uma linha no YAML. **Remover** é apagar a linha. A camada padronizada é derivada do bruto, então o caminho normal é refazê-la (`padronizar --refazer`) em vez de migrar. Colunas novas também podem ser acrescentadas sem refazer (`ALTER TABLE ADD COLUMN`, gerado pelo motor).

Tabelas que **não** podem ser refeitas (a chave própria de pessoa e a ponte de identificadores, ADR 0004) usam migrações numeradas em SQL, aplicadas em ordem e registradas em `controle.migracao`.

### 2. Configuração central

Um arquivo `configuracao.yml` na raiz (sem segredo; segredos vêm de variável de ambiente) é a única fonte de verdade para:

```yaml
dados:
  pasta: dados                       # onde ficam bruto e bancos (variável: QUEM_DECIDIU_PASTA)
banco:
  url: "sqlite:///{pasta}/{camada}.db"   # PostgreSQL: postgresql://.../quem_decidiu, esquema = camada
```

Hoje a pasta muda em dois lugares (`--pasta`, nos dois programas) e a URL da fonte em `conjuntos.py`; depois desta decisão, URL na especificação da fonte e pasta e banco na configuração.

### 3. Acesso ao banco por uma camada própria, sobre SQLAlchemy Core

O código deixa de importar `sqlite3`. Um módulo `nucleo/armazenamento.py` expõe poucas operações (criar tabela a partir da especificação, upsert em lote, executar SQL de uma camada, ler) sobre **SQLAlchemy Core**, que traduz para SQLite, PostgreSQL e DuckDB. O SQL das camadas integrado e servico fica em arquivos `.sql` (um por tabela), em vez de texto dentro do Python, escrito em SQL padrão e executado pelo mesmo módulo; quando o PostgreSQL entrar, esses arquivos migram para modelos do dbt-core (ADR 0002) sem mudança de lógica.

### 4. Extração completa e incremental

A especificação declara a estratégia de cada conjunto, e a linha de comando a usa:

| Modo | Comando | O que faz |
| --- | --- | --- |
| **Histórico (massivo)** | `extrair --historico --de 2001 --ate 2026` | baixa todos os anos pedidos de todos os conjuntos anuais; usado na primeira carga e em recargas |
| **Incremental** | `extrair --incremental` | baixa só o que pode ter mudado: conjuntos `completa` e os anos não estáveis (o corrente e o anterior); anos estáveis já capturados são pulados |
| **Condicional** | automático nos dois modos | pergunta à fonte se o arquivo mudou (`ETag`/`Last-Modified`/tamanho) antes de baixar; se não mudou, só atualiza `ultima_verificacao` |

A padronização passa a processar só as capturas ainda não padronizadas (`controle.captura.padronizada_em`), com `--refazer` para tudo. Integração e serviço continuam reconstruídos por completo nesta decisão (a carga atual leva alguns minutos); a versão incremental dessas camadas fica para os modelos incrementais do dbt.

### 5. Sobre Spark

Spark **não** entra agora. O volume é de cerca de 1,4 milhão de linhas (alguns minutos em SQLite; segundos em DuckDB ou PostgreSQL), e Spark custa operação e aprendizado sem ganho nessa escala. O que esta decisão faz para não fechar a porta:

- a especificação YAML descreve a transformação sem depender do motor; um executor Spark poderia ler o mesmo YAML e as regras de limpeza seriam reescritas como funções do Spark;
- o SQL das camadas altas é padrão e roda em Spark SQL, DuckDB e PostgreSQL com poucos ajustes;
- o bruto continua sendo arquivo, que Spark lê direto.

Reabre-se a discussão quando um conjunto passar de dezenas de milhões de linhas ou quando houver necessidade de processamento distribuído medida.

## Dependências novas (exigem aprovação, conforme o AGENTS.md)

| Dependência | Para quê | Alternativa descartada |
| --- | --- | --- |
| **PyYAML** | ler `fonte.yml` e `configuracao.yml` | `tomllib` (já na biblioteca padrão, mas o fundador pediu YAML); JSON (ruim para comentar) |
| **SQLAlchemy** (Core, sem ORM) | DDL e upsert independentes de banco | escrever um adaptador próprio para cada banco (reinventa a roda); DuckDB como motor único (prende ao DuckDB) |

Nenhuma outra. O código de leitura de CSV, regras de texto e orquestração continua na biblioteca padrão. Dagster e dbt-core seguem decididos no ADR 0002 e entram quando houver agendamento e o PostgreSQL.

## Alternativas consideradas

- **Manter o código como está e só refatorar:** não resolve acrescentar coluna em um lugar só nem trocar de banco.
- **dbt-core já para todas as camadas:** ótimo para integrado e servico, mas não faz extração nem leitura de CSV por especificação; entra depois, não no lugar do YAML.
- **Framework de ingestão pronto (Airbyte, dlt, Meltano):** resolveriam parte da extração, mas as fontes aqui são arquivos públicos simples e a regra de neutralidade, linhagem e minimização de dados exige controle fino; o custo de adaptar supera o de escrever um motor pequeno.
- **ORM completo:** mais abstração do que o projeto precisa.

## Consequências

- Refatoração maior: o `padronizar.py` da Câmara é substituído por `fonte.yml` mais um motor genérico e poucos ganchos (por exemplo, a lista de siglas de ementas e as tabelas derivadas dos votos).
- Os testes atuais continuam valendo (comparam o resultado, não a implementação); acrescentam-se testes do motor com uma fonte fictícia, para provar que uma fonte nova entra só com YAML.
- Nova fonte (Senado, TSE) = novo `fonte.yml` mais os ganchos que ela precisar.
- O catálogo de dados passa a ser gerado do YAML, o que elimina a duplicação e a chance de divergir.
- A conformidade (princípio IX) fica mais fácil de provar: `nunca_ler` é verificável por teste em qualquer fonte.

## Referências do mercado

O padrão "engine que lê YAML" existe e é comum. Os exemplos abaixo foram pesquisados em 2026-10-20 (leitura de documentação; nenhum foi instalado ou testado aqui):

| Referência | O que faz | O que o projeto aproveita |
| --- | --- | --- |
| [Airbyte, CDK de baixo código](https://docs.airbyte.com/platform/connector-development/config-based/low-code-cdk-overview) | O conector é um manifesto YAML (fluxos, esquema, paginação); o CDK mapeia o YAML para o comportamento | fonte descrita em YAML, motor único, código só para o que o YAML não cobre |
| [Dagster Components](https://docs.dagster.io/guides/build/components/building-pipelines-with-components/adding-component-definitions) | `defs.yaml` com `type` (a classe) e `attributes`; o YAML aponta para código Python por caminho de módulo | **o YAML escolhe qual código roda**, por nome de módulo; é o caminho natural quando o Dagster entrar (ADR 0002) |
| [Kedro, catálogo de dados](https://docs.kedro.org/en/latest/catalog-data/introduction/) | os datasets ficam em `catalog.yml`; o código só os chama pelo nome; há sobreposição por ambiente | declaração separada do código; configuração por ambiente (`conf/base`, `conf/local`) |
| [Meltano](https://motherduck.com/glossary/meltano.md) | fontes, destinos e transformações declarados em `meltano.yml` e executados por CLI | pipeline inteiro versionado como declaração |
| [dlt-meta, da Databricks](https://docs.databricks.com/aws/dlt-ref/dlt-meta) | motor em Python gera pipelines bronze e prata a partir de metadados JSON e YAML | mesma ideia de camadas (bruto, padronizado) dirigidas por metadados; mostra que o padrão vale também em Spark |
| [Ververica Data Ingestion](https://docs.ververica.com/byoc/user-guides/admin-operator-guide/data-ingestion/) | trabalhos de ingestão em YAML, com variáveis por ambiente | variáveis e substituição por ambiente |
| [Cerc: de notebooks para contratos YAML](https://building.cerc.com/en/blog/declarative-stack-data-lake-ingestion-at-scale/) | contratos YAML (fonte, destino, esquema, regras de publicação) sobre runtime reutilizável | contrato por fonte com esquema e regras; caso de produção do padrão |
| [OpenIngest](https://libraries.io/pypi/openingest) e [Lotos](https://pypi.org/project/lotos/) | pacotes Python de ETL dirigido por um YAML; Lotos descobre conectores e transformações por registro | validam o desenho; ambos pequenos e pouco maduros, por isso não são dependência |

Em comum: (1) o YAML descreve **o quê**; (2) um motor genérico faz o **como**; (3) o que foge do padrão é um **ponto de extensão nomeado no YAML**, que aponta para código; (4) declaração e código ficam em lugares diferentes. Os pacotes prontos (Airbyte, Meltano, dlt) resolveriam parte da extração, mas não da neutralidade, da linhagem e da minimização de dados exigidas aqui; por isso o motor é próprio e pequeno, seguindo o mesmo padrão. dbt segue o mesmo princípio para SQL (`sources.yml` e modelos), conhecimento de referência não pesquisado nesta data.

## Separação entre declaração e código (proposta)

Hoje o `fonte.yml` fica dentro do pacote Python, ao lado do código. Pelo padrão acima, as declarações passam a viver fora do código:

```text
declaracoes/                       # só declaração: YAML e SQL; nada de Python
  configuracao.yml                 # pasta, banco, agendamento (sobreposição por ambiente)
  pipeline.yml                     # etapas, ordem, dependências e o código de cada etapa
  fontes/
    camara.yml                     # URL, formato, conjuntos, tabelas, colunas, regras
  modelo/
    controle.yml  integrado.yml  servico.yml
  sql/
    integrado/camara/*.sql         # transformações declaradas em SQL
    servico/*.sql
src/quem_decidiu/dados/            # só código: o motor e os pontos de extensão
  nucleo/ ...                      # motor genérico (lê os YAML)
  extensoes/camara.py              # ganchos específicos da fonte (siglas de ementa)
```

`pipeline.yml` declara o que roda e em que ordem; cada etapa aponta para o código por caminho de módulo, como os `defs.yaml` do Dagster:

```yaml
etapas:
  extrair:     {executor: quem_decidiu.dados.nucleo.extracao:extrair_plano}
  padronizar:  {executor: quem_decidiu.dados.nucleo.motor:padronizar_tudo, depende_de: [extrair]}
  integrar:
    executor: quem_decidiu.dados.integracao.camara:integrar      # específico da fonte
    depende_de: [padronizar]
  servir:      {executor: quem_decidiu.dados.servico.construir:construir, depende_de: [integrar]}
  verificar:   {executor: quem_decidiu.dados.qualidade.verificacoes:executar, depende_de: [servir]}
```

Consequências: a ordem do pipeline e a escolha do código deixam de estar no Python; acrescentar fonte é acrescentar `declaracoes/fontes/<fonte>.yml` e, se preciso, um módulo de extensão; o motor continua o mesmo; o mesmo YAML pode ser lido depois por um componente do Dagster. O custo é uma camada de indireção (nomes de módulo em texto), compensada por um teste que valida todo `executor` e todo gancho citado nos YAML.
