# ADR 0054: Fato, agregado, medição e avaliação

- **Status:** aceito em 2026-11-12 (decisão do fundador); antes proposto
- **Data:** 2026-11-11
- **Complementa:** a regra "sem ranking, nota ou métrica avaliativa" do `AGENTS.md` e da [visão geral](../01-entender/01-visao-geral.md) (itens 5 e 6), o [ADR 0033](0033-marts-com-a-terminologia-da-dbt-labs.md) (prefixos dos marts), o [ADR 0039](0039-marts-como-camada-semantica.md) (derivado marcado, mudança só aditiva) e o [ADR 0053](0053-nucleo-sem-nomes-de-fonte.md) (item 3, verificações com colunas próprias).
- **Para quem é:** quem cria um mart novo ou revisa um. Responde: em que categoria cai uma métrica, onde ela mora, como o método é publicado e o que impede que uma avaliação entre no lake.
- **Origem:** Refs #278 (diagnóstico, item D1); base da fase 2, "Observatório da transparência" (#279).

## Contexto

A regra proíbe ranking, nota e métrica avaliativa derivada. A fase 2 quer publicar o que as fontes oficiais deixam de entregar (indisponibilidade, atraso, arquivo truncado, mudança de esquema, divergência entre fontes) e desde quando. Sem uma fronteira escrita, "completude da fonte X em 2026" pode ser lida como avaliação, e um "índice de transparência" pode entrar pela mesma porta. Já existem agregados sobre pessoas que ninguém contesta (`agg_pessoas_atividade`, com contagem de votos e de propostas; `percentual_votos_validos` em `fct_resultados`): a fronteira precisa explicar por que eles valem.

Três referências públicas:

- O [índice do DadosJusBr](https://dadosjusbr.org/indice) mede cada órgão em duas dimensões (completude, seis critérios; facilidade, quatro critérios), com peso igual, e as combina numa **nota única de 0 a 1** (média harmônica). O método é público, mas a combinação e os pesos são escolha do projeto.
- O [Pelican](https://pelican-backend.readthedocs.io), da Open Contracting, verifica a qualidade em quatro níveis (campo, registro, conjunto de dados e tempo), cada verificação com resultado próprio, sem nota.
- O [modelo de *statements* do OpenSanctions](https://www.opensanctions.org/docs/statements/) guarda cada afirmação com a fonte (`dataset`) e as datas em que o pipeline a viu pela primeira e pela última vez (`first_seen`, `last_seen`): a proveniência e o "desde quando" vêm na linha.

## Decisão

1. **Quatro categorias.**

   | Categoria | O que é | Exemplo genérico | Onde mora |
   | --- | --- | --- | --- |
   | **Fato** | o que a fonte oficial afirma ou o que a plataforma observou ao buscar a fonte, uma linha por ocorrência, com fonte e captura | "a Pessoa Exemplo votou sim na votação V"; "a fonte F respondeu 404 ao pedido do mês M" | `fct_`, `dim_`, `brg_` |
   | **Agregado** | contagem, soma, mínimo, máximo ou razão entre contagens de **um** fato publicado, reproduzível por SQL a partir dele, sem parâmetro escolhido por nós | "quantidade de votos da Pessoa Exemplo na legislatura L"; "percentual dos votos válidos na disputa D" | `agg_` |
   | **Medição** | agregado cuja unidade é uma **fonte, dataset ou órgão como publicador de dado**, nunca uma pessoa; uma medida por coluna, com método público | "dias sem arquivo novo do dataset D"; "linhas sem a coluna C na partição P"; "capturas truncadas por mês" | `agg_fontes_<medida>` e `fct_fontes_ocorrencias` (item 3) |
   | **Avaliação** | juízo de valor: nota, ranking, posição, índice que combina medidas com pesos, limiar que qualifica ("baixa", "insuficiente"), comparação de pessoas por critério nosso | "índice de transparência 0,62"; "o 3º órgão mais aberto"; "parlamentar pouco atuante" | **não entra no lake**, para nenhuma unidade |

   Conteúdo gerado por IA não é fato nem agregado: continua em tabelas próprias, rotulado com modelo e versão (regra vigente); este ADR não cria o prefixo, que se decide com a primeira tabela desse tipo.

2. **Critério para uma métrica nova**, nesta ordem (a primeira resposta "sim" decide):
   1. Exige peso, nota, ordenação entre unidades ou um limiar que qualifica? **Avaliação**: não entra. Quem consome o lake pode montar a sua, sob a sua responsabilidade.
   2. Copia o que a fonte publica, ou registra o que a busca observou, uma linha por ocorrência? **Fato.**
   3. A unidade é fonte, dataset ou órgão publicador e o número descreve a publicação, não a conduta de quem aparece no dado? **Medição.**
   4. É contagem, soma ou razão de um fato, sem parâmetro nosso? **Agregado** (vale para pessoas).
   5. Nenhuma das anteriores: proponha um ADR.

   Uma medida que depende de uma expectativa (atraso) só usa expectativa que tenha fonte: o prazo legal ou a periodicidade declarada pela própria fonte, citados na descrição. Sem isso, publica-se o intervalo bruto ("dias desde a última publicação"), não o atraso.

3. **Nomes e lugar.** Sem prefixo novo: a medição é um `fct_` ou um `agg_` com o tema `fontes` na frente, em `dbt/models/marts/fontes/`. `fct_fontes_ocorrencias` traz uma linha por ocorrência (tipo, fonte, dataset, partição, primeira e última observação, como o `first_seen`/`last_seen` do OpenSanctions) e a evidência: `id_verificacao` sempre (a linha de `metadata.fontes_verificacoes`, com as colunas do ADR 0053, item 3) e `id_captura` quando houver arquivo. As medidas seguem os quatro níveis do Pelican (campo, registro, conjunto de dados, tempo) e se chamam `agg_fontes_<medida>`. O que descreve o nosso processamento, e não a fonte (execuções, resultado bruto dos testes do dbt), fica em `metadata`; quais dessas tabelas se publicam, como `metadata/capturas`, é decisão do #279.

4. **Método público.** O método é o SQL do modelo (no repositório, com a versão em `metadata.exportacao.versao_commit`) e a descrição da tabela e de cada coluna, que diz a unidade, o que entra, o que fica de fora e a origem de qualquer expectativa; a descrição vai no rodapé do Parquet como as demais. O documento de cobertura e lacunas (`docs/03-consultar/04-cobertura-e-lacunas.md`) passa a ser gerado dessas tabelas, como o catálogo. **Mudar o método é mudar o significado** da coluna: entra coluna nova e a antiga segue até o aviso (ADR 0039, item 2).

5. **Trava por teste**, em `tests/test_names_and_descriptions.py` (que já lê o warehouse e os tipos):
   - nenhuma coluna de mart tem, entre as partes do nome separadas por `_`, `rank`, `ranking`, `score`, `pontuacao`, `indice` ou `posicao`; e `nota` só em coluna de texto (a `nota` de `fct_constituicao_alteracoes` é o texto da nota da norma). A comparação é por parte, não por trecho: `id_proposicao` passa;
   - nenhuma tabela `*_fontes_*` tem `id_pessoa` nem coluna marcada com `meta: {pii: true}`: medir a fonte não mede pessoa;
   - toda tabela `*_fontes_*` traz `fonte` e, se `fct_`, `id_verificacao`.

   A lista de palavras pega o descuido, não a má-fé; a revisão humana do PR continua sendo a trava principal, e este critério é o que ela aplica.

## Alternativas consideradas

- **Não publicar medições:** sem risco algum, mas a lacuna da fonte fica invisível ao público, e é ela que explica um campo vazio na ficha. Contraria o objetivo da fase 2 e a regra de que o teste mede a lacuna. Descartada.
- **Publicar só internamente** (relatório do `observe` e do Elementary, ADR 0018): é o que existe hoje. Não é auditável por quem consome o lake, e a pergunta "o que este órgão deixou de publicar e desde quando" não se responde com uma consulta. Descartada.
- **Índice com nota, como o DadosJusBr:** comunica melhor e já tem precedente sério. Mas os pesos e a forma de combinar são opinião, a nota vira ranking assim que alguém ordena, e a manchete ("órgão X tirou 0,3") cai sobre o projeto. Publicar as medidas separadas dá a qualquer um os insumos para montar o próprio índice. Descartada; reabre só por ADR novo, com método externo já aceito (não nosso).
- **Prefixo próprio para medição** (`med_`): deixaria a categoria visível no nome, mas é estrutura nova para o que `fct_`/`agg_` e o tema `fontes` já dizem; o teste do item 5 confere pelo tema.

## Consequências

- O #279 pode publicar ocorrências e medidas das fontes sem esbarrar na regra, e com o critério do item 2 cada mart novo tem resposta sem consulta ao fundador.
- `agg_pessoas_atividade` e `percentual_votos_validos` ficam explicitamente permitidos (agregados de um fato, sem parâmetro nosso). Um "índice de atuação" de parlamentar fica explicitamente proibido.
- **Risco reputacional:** medir um órgão é publicar algo desconfortável para ele. Mitigação: cada linha aponta a evidência (verificação, captura, hash) e a expectativa só vem de fonte citada; um erro nosso se corrige refazendo do landing, e a ocorrência causada por falha nossa (rede, código) não é atribuída à fonte (o tipo da ocorrência distingue).
- **LGPD:** a unidade é o publicador, não o servidor que publica; nenhuma tabela de fontes leva pessoa (item 5). Em órgão pequeno, a medida pode apontar indiretamente para quem responde por ela; o texto e a descrição falam sempre da publicação, nunca de quem a faz ([LGPD no projeto](../01-entender/07-lgpd-dados-pessoais.md)).
- Depende do ADR 0053, item 3 (colunas próprias em `metadata.fontes_verificacoes`): sem elas, o tipo da ocorrência sai de texto livre.
- Documentação no PR que implementar: `docs/03-consultar/02-convencao-de-nomes.md` (tema `fontes` e as palavras proibidas) e a visão geral (link para este ADR).
