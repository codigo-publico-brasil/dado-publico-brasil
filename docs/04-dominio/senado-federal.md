# Senado Federal: o que os dados dizem

Para quem quer entender os campos que a plataforma traz do Senado. A fonte é a API de dados abertos (`https://legis.senado.leg.br/dadosabertos`); a declaração está em [`sources/legislativo/federal/senado.yml`](../../sources/legislativo/federal/senado.yml).

## O que é

O Senado Federal é a casa dos estados da Câmara alta do Congresso Nacional: 81 senadores, três por estado, com mandato de oito anos. A cada quatro anos renova-se um terço e depois dois terços das cadeiras, por isso o mandato de um senador atravessa **duas legislaturas** (a legislatura dura quatro anos e é comum às duas casas). Cada senador tem dois suplentes, que assumem na vacância ou no afastamento do titular.

## Votações e votos

- **Votação nominal:** cada senador registra o voto; a plataforma guarda o texto da sigla como a fonte informa.
- **Votação secreta:** a fonte não revela a escolha. Cada senador aparece com a sigla `Votou`, que significa apenas que participou. Em `fct_votacoes`, `fl_votacao_secreta` é verdadeiro.
- **Totais** de Sim, Não e Abstenção vêm preenchidos só em parte das votações; quando faltam, ficam vazios.

Siglas de voto que a fonte usa (a descrição é a da própria fonte):

| Sigla | Significado informado |
| --- | --- |
| `Sim`, `Não`, `Abstenção` | voto registrado |
| `Votou` | participou de votação secreta |
| `P-NRV` | presente, não registrou voto |
| `AP` | atividade parlamentar |
| `LS` | licença saúde |
| `LP` | licença particular |
| `MIS` | missão da Casa no país ou no exterior |
| `NCom` | não compareceu |
| `Presidente (art. 51 RISF)` | o presidente da sessão vota só em caso de empate |
| `NA` | dispositivo não citado |

## Matérias

A plataforma traz as matérias que aparecem em votações (sigla, número, ano, ementa e data de apresentação), com o link para a página oficial da matéria. O **processo** de cada matéria (situação atual e a **norma gerada**: tipo, número, datas e veículo de publicação) vem da API, uma chamada por matéria, sob pedido (`--foreach`): preenche `situacao` e o mart `fct_normas_geradas`. Em parte das respostas a fonte não informa a situação atual, e o campo fica vazio. A autoria está no raw e a tramitação no landing, mas ainda não nos marts.

## O que ainda não vem do Senado

Redes sociais dos senadores, votos em comissões, a tramitação das matérias e as autorias (issue 14). O nascimento, a naturalidade e a foto vêm do detalhe por senador (`senadores_detalhe`), e o exercício real (titular e suplente, períodos e causas de afastamento) está em `fct_exercicios`.
