# Identidade de pessoas

Problema: uma mesma pessoa pode aparecer em várias fontes e em vários cargos. Quem foi deputado, depois senador, depois ministro ou presidente tem, em cada fonte, um identificador diferente. Se a "pessoa" do projeto fosse o cadastro de deputados da Câmara, o senador seria outra pessoa, e a história se perderia.

## A solução: três tabelas

```text
        identity.pessoa                   identity.pessoa_identificador             marts.mandatos
  ┌──────────────────────────┐        ┌───────────────────────────────────┐   ┌─────────────────────────────┐
  │ id_pessoa  (chave nossa) │◄───────│ id_pessoa                         │   │ id_pessoa                   │
  │ nome, nome_civil         │        │ fonte        ex.: camara          │   │ cargo   Deputado federal    │
  │ nascimento, foto, redes  │        │ tipo_id      ex.: deputado        │   │ casa    Câmara dos Deputados│
  └──────────────────────────┘        │ id_na_fonte  ex.: 74161           │   │ legislatura, uf             │
            ▲                         │ metodo, confirmado_por, data      │   │ inicio, fim (oficiais)      │
            └─────────────────────────┴───────────────────────────────────┘   └─────────────────────────────┘
```

- **`pessoa`:** a pessoa do projeto, com chave própria (`id_pessoa`) que não significa nada fora do projeto e nunca muda.
- **`pessoa_identificador`:** a ponte. Uma pessoa tem vários identificadores (Câmara, Senado, TSE...). Cada ligação registra o **método** (como foi ligada), **quem confirmou** e **quando**.
- **`mandato`:** o que a pessoa foi e quando. Mudar de cargo cria outro mandato, não outra pessoa.

> **Conceito: chave substituta (*surrogate key*).** Usar o identificador de uma fonte como chave da entidade prende o projeto àquela fonte. A chave própria isola o modelo das fontes: trocar ou acrescentar fonte não muda quem a pessoa é.

> **Conceito: tabela-ponte de identificadores (*crosswalk*, parte do que o mercado chama de MDM, gestão de dados mestres).** É a peça que permite juntar sistemas que não compartilham chave. Em ambientes corporativos o mesmo problema aparece como "cliente duplicado em três sistemas".

## O caso "deputado que virou senador e presidente"

| Momento | Fonte | Identificador | O que se grava |
| --- | --- | --- | --- |
| Deputado federal | Câmara | `camara / deputado / 12345` | 1 pessoa, 1 identificador, mandato "Deputado federal" por legislatura |
| Depois, senador | Senado | `senado / parlamentar / 6789` | **mesma** pessoa; novo identificador; mandato "Senador" |
| Depois, candidato a presidente | TSE | `tse / candidato / 123456` | **mesma** pessoa; novo identificador |
| Presidente eleito | TSE, DOU | (mesmo identificador do TSE) | mandato "Presidente da República" |

O que **liga** os identificadores é a regra de ligação, e ela é o ponto delicado.

## Regra de ligação (conservadora)

Decidida na spec 008: um erro de ligação (juntar duas pessoas diferentes, ou separar uma só) distorce quem votou em quê, e isso é pior do que deixar duas pessoas separadas por um tempo. Por isso:

1. **Ligação automática por identificador oficial:** só quando uma chave oficial constar nas duas fontes.
2. **Ligação por nome civil e data de nascimento** ([ADR 0013](../05-decisoes/0013-tse-ligacao-por-nome-civil-e-nascimento.md)): só quando os dois são **iguais e únicos**. Nome sem acento, em minúsculas e com espaços únicos; "único" quer dizer que, dentro de cada fonte, só um registro tem aquele par (homônimo com a mesma data não liga) e, numa eleição, só uma candidatura o tem. É o que liga a candidatura do TSE à pessoa e o deputado ao senador que são a mesma pessoa.
3. **Nunca** ligar só por nome, nem por nome e ano de nascimento. Há homônimos, e nomes de urna se repetem.
4. Caso ambíguo ou sem correspondência (nome grafado diferente entre as fontes, nascimento ausente) **não liga**, é medido por teste e a curadoria manual decide. A curadoria é a tabela [`vinculos_aprovados.csv`](../../dbt/seeds/vinculos_aprovados.csv): cada linha liga um registro de origem a um de destino, com quem aprovou, quando e a evidência escrita; o método gravado é "vínculo aprovado por ...". Um teste barra linha que aponta para registro inexistente. Só uma pessoa edita essa tabela; o código nunca a preenche.
5. Toda ligação é registrada com método e data (`identity.pessoa_identificador`), e uma fusão entre casas fica em `identity.pessoa_fusao`.

### Fusão de chaves

Quando a regra mostra que um deputado e um senador são a mesma pessoa, a chave mais **nova** é absorvida pela mais **antiga**: os identificadores passam a apontar para a sobrevivente, a chave absorvida sai de `identity.pessoa` e **nunca é reaproveitada**, e a fusão fica em `identity.pessoa_fusao` (mart `pessoas_fusoes`) para quem guardou a chave antiga resolver a atual. `marts.pessoas` tem uma linha por pessoa (dados da Câmara quando está nas duas casas; coluna `fontes` com todas).

Hoje só existe a fonte Câmara, então toda ligação é a automática "identificador oficial da própria fonte". O código está em [`identity.py`](../../src/dado_publico_brasil/transformation/identity.py) e as tabelas são criadas por [migração](../../ddl/0002_identity.sql). Os dados da pessoa (nome, foto, nascimento) e o mandato são modelos SQL do dbt ([`int_pessoas_unidas_cadastro`](../../dbt/models/intermediate/int_pessoas_unidas_cadastro.sql) e [`mandatos`](../../dbt/models/marts/legislativo/mandatos.sql)).

## Pessoa de todo eleito ([ADR 0031](../05-decisoes/0031-pessoas-de-todo-eleito.md))

Além do parlamentar da Câmara e do Senado, **todo candidato eleito pelo menos uma vez** ganha pessoa, a partir da primeira execução depois da eleição (inclui vereador). As outras candidaturas dele (as que perdeu, antes ou depois) entram na mesma pessoa; quem nunca foi eleito não tem pessoa.

- **A âncora é a candidatura** (`id_candidatura`, estável), na ponte com o tipo `candidatura_de_eleito`. O `id_pessoa_tse` agrupa as candidaturas, mas o rótulo dele muda quando entra uma candidatura com outro nome; por isso ele nunca é o identificador.
- **Se um grupo toca duas pessoas, elas se fundem.** A pessoa da Câmara ou do Senado sobrevive sempre (a chave dela já foi publicada). **Duas pessoas oficiais nunca se fundem por aqui**: o caso aparece no teste `pessoas_de_grupo_do_tse_com_mais_de_uma_pessoa` e entra em `vinculos_aprovados` se uma pessoa confirmar.
- Os atributos (nome, nascimento, gênero) ficam em `core.pessoas`, cada um com a fonte de onde veio.
- Os riscos e o teste de cada um estão na [issue 130](https://github.com/codigo-publico-brasil/dado-publico-brasil/issues/130).

## Mandato: o que é oficial e o que é observado

O arquivo de deputados da Câmara informa a primeira e a última legislatura, mas não que o deputado serviu em todas as legislaturas do intervalo (houve suplentes, licenças e interrupções). Por isso o projeto não deduz mandato dessas duas datas.

Hoje o mandato nasce dos **votos observados**: existe um mandato por pessoa e legislatura em que há voto registrado, com a UF do voto mais recente. `inicio` e `fim` oficiais ficam **vazios** até entrar uma fonte que os informe (por exemplo, a composição por legislatura da Câmara ou o TSE). As colunas `primeiro_voto_observado` e `ultimo_voto_observado` mostram só o que foi visto, e `base` diz de onde o mandato veio.

> **Conceito: não completar o que a fonte não diz.** Campo vazio com a origem explicada é mais confiável do que campo preenchido por estimativa. A página mostrará "sem informação" em vez de um valor inventado.

## O que ainda não existe e o que decidir quando entrar

- **Partido por data.** O partido de um voto vem do arquivo de votos (`sigla_partido_na_data`). Filiação partidária por período exigiria o TSE; fica em aberto.
- **Pessoa que nunca foi parlamentar** (ministro, presidente, vereador). Entra com outras fontes; o modelo já comporta (uma pessoa, um identificador, um mandato).
- **Proposição entre casas.** Um projeto aprovado na Câmara segue ao Senado com outro número. Hoje proposição se identifica por (`fonte`, `id_na_fonte`); a relação "é a mesma proposição" entre casas será modelada quando o Senado entrar.
- **Pessoa privada.** Nenhuma pessoa privada entra no modelo; só agentes públicos no exercício da função.
