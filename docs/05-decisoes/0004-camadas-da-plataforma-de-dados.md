# ADR 0004: Camadas da plataforma de dados e identidade de pessoas

- **Status:** aceito (2026-10-20, pelo fundador). A estrutura de pastas, o banco e os nomes das camadas foram substituídos pelos ADRs 0005 a 0007; a ideia de camadas e a regra de identidade continuam valendo.
- **Data:** 2026-10-20
- **Contexto do projeto:** a primeira carga da Câmara foi feita num único módulo (`camara/`), que baixa, grava o bruto, interpreta e carrega no banco no mesmo lugar, com a página de exploração dentro do pacote. Funciona para validar, mas mistura responsabilidades e não permite agendar, medir frescor nem juntar outras fontes.

## Contexto

Dado público de várias casas (Câmara, Senado, TSE, DOU, município) só vira informação confiável se cada etapa tiver uma responsabilidade clara, um dono, um teste e um registro de quando rodou. O projeto também serve de estudo de arquitetura de dados corporativa, então as camadas devem seguir nomes e práticas conhecidos do mercado.

## Decisão

### 1. Quatro camadas de dados

| Camada | Nome no projeto | Equivale a | O que guarda | Regra |
| --- | --- | --- | --- | --- |
| 1 | **bruto** | raw, landing, bronze | arquivo ou resposta exatamente como veio, com hash, URL, data de captura e execução | imutável; nunca editado nem apagado |
| 2 | **padronizado** | staging, silver | uma tabela por conjunto da fonte, com tipos, datas, caixa e codificação padronizados; ainda sem juntar fontes | derivado do bruto, reproduzível; tabelas com o prefixo da fonte (`camara_`, `senado_`) |
| 3 | **integrado** | core, modelo conformado | entidades do projeto, independentes da fonte: pessoa, mandato, proposição, votação, voto, partido, órgão | única camada que conhece mais de uma fonte; regras de identidade vivem aqui |
| 4 | **servico** | marts, gold, camada de consumo | visões prontas para consumo (portal, API, explorador, exportações) | só leitura; consumidores nunca leem as camadas 1 a 3 |

Cada linha do padronizado e do integrado aponta para a captura de que veio (`id_captura`, em `controle.captura`) e, por ela, para o arquivo bruto e a execução que o trouxe. `controle` (execuções, capturas, resultado dos testes) é um esquema transversal, não uma camada de dados. É isso que dá a linhagem "do número na tela ao documento original".

### 2. Etapas do pipeline (ETL/ELT)

Cada fonte tem três etapas separadas, cada uma uma função que pode rodar sozinha e rodar de novo sem mudar o resultado:

1. **extrair:** fonte oficial para o bruto. Só rede e disco; não interpreta.
2. **padronizar:** bruto para padronizado. Só lê o bruto; não acessa a rede.
3. **integrar:** padronizado (de uma ou mais fontes) para o integrado e depois o servico.

Cada etapa registra em `execucao`: início, fim, versão do código, linhas lidas e gravadas, resultado. Isso serve ao frescor, à auditoria e ao agendamento. Hoje as etapas são chamadas por uma linha de comando; elas são escritas como funções com entradas e saídas declaradas, para que o Dagster (ADR 0002) as envolva como ativos sem reescrever a lógica.

### 3. Estrutura do código

```text
src/quem_decidiu/
  dados/
    nucleo/          # execução, hash, manifesto, conexão, registro de execuções
    fontes/
      camara/        # extrair.py, padronizar.py (nada de outra fonte aqui)
      senado/        # idem, quando entrar
    integracao/      # identidade de pessoas, mandatos, modelo integrado
    servico/         # visões de consumo
    qualidade/       # testes de dados: unicidade, integridade, completude, reconciliação
    catalogo/        # dicionário de dados em código (dono, sensibilidade, frescor esperado)
ferramentas/
  explorador/        # página de exploração: fora do pacote, só lê o servico, apagável
tests/               # espelha a estrutura acima
```

A regra de dependência é de cima para baixo: `servico` lê `integrado`, `integrado` lê `padronizado`, `padronizado` lê `bruto`. Uma fonte nunca importa outra. O explorador e, depois, o portal importam só o `servico`.

### 4. Banco local e banco do piloto

- Hoje: SQLite, um arquivo por camada, abertos com `ATTACH` para que as consultas usem o nome qualificado (`padronizado.camara_proposicao`).
- Piloto (ADR 0002): PostgreSQL, com um esquema por camada. O SQL é o mesmo; troca-se a conexão.

### 5. Identidade de pessoas (modelo integrado)

Pessoa é uma entidade do projeto, não da Câmara. A mesma pessoa pode ser deputada, depois senadora, depois ministra ou presidente, e cada fonte a identifica de um jeito.

- `pessoa`: chave própria do projeto (`id_pessoa`, sem significado), nome de exibição padronizado, nome civil, data de nascimento, dados públicos.
- `pessoa_identificador`: ponte entre a chave do projeto e a chave de cada fonte (`fonte`, `id_na_fonte`, `id_pessoa`, método da ligação, quem confirmou, data). Uma pessoa tem vários identificadores.
- `mandato`: o que a pessoa foi e quando (`id_pessoa`, cargo, casa ou ente, UF, partido no início, início, fim, fonte). Mudar de cargo cria outro mandato, não outra pessoa.
- **Regra de ligação:** conservadora, como já decidido na spec 008. Ligar automaticamente só por chave oficial que conste nas duas fontes; por nome e data de nascimento, só como sugestão para revisão humana; nunca por nome sozinho. Toda ligação é registrada e pode ser desfeita.
- O identificador da Câmara deixa de ser a chave da pessoa. É um identificador na ponte.

### 6. Governança, segurança e qualidade como parte das camadas

- **Catálogo:** cada tabela tem dono, descrição, sensibilidade, fonte, frescor esperado e regra de retenção, em código versionado e publicado em `docs/dados/`.
- **Sensibilidade:** dado público de agente público é permitido; documentos pessoais (CPF, RG, e similares) nunca entram em nenhuma camada (princípio IX da constituição).
- **Qualidade:** testes em cada camada (unicidade, chaves estrangeiras, preenchimento, formato, reconciliação com os totais da fonte). Teste que falha bloqueia a promoção para a camada seguinte.
- **Frescor:** cada conjunto declara o atraso aceitável; a página de qualidade mostra a última execução bem-sucedida e o atraso real.
- **Acesso:** consumidores abrem o banco só para leitura e só a camada `servico`. Nenhum segredo no repositório.
- **Texto reescrito por IA:** nunca substitui a fonte. Se vier a existir, é campo derivado separado, rotulado como gerado por IA, com modelo, versão e data, e depende de spec própria.

## Alternativas consideradas

- **Manter um módulo por fonte com tudo dentro:** é o que existe hoje; cada fonte nova repete a mistura e a identidade de pessoa fica presa à primeira fonte.
- **Duas camadas (bruto e curado):** o que o ADR 0002 já descreve; falta a separação entre limpar uma fonte e juntar várias, que é onde estão os erros mais caros.
- **Esquema em estrela completo (dimensões e fatos):** vale para análise, não para páginas por entidade; a camada de servico pode ter tabelas assim se uma consulta pedir.
- **Dagster e dbt desde já:** continuam decididos no ADR 0002, mas só entram quando houver duas fontes ou o primeiro agendamento; até lá, funções e uma linha de comando, sem dependência nova.

## Consequências

- É preciso refatorar o código existente (separar `camara/` em extrair e padronizar, criar o integrado e o servico, mover o explorador) e trocar a chave de pessoa; os testes atuais são movidos junto.
- Cada nova fonte (Senado, TSE, DOU) segue o mesmo molde de duas pastas e testes.
- Mais tabelas e mais passos que antes; em troca, frescor, linhagem e identidade passam a ser medidos e testados.
- O ADR 0002 não muda; este ADR o detalha (camadas, forma do código) e entra em vigor quando aceito.
