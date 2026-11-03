# Tribunal Superior Eleitoral: o que os dados dizem

Para quem quer entender os campos que a plataforma traz do TSE. A fonte é o portal de dados abertos (`https://dadosabertos.tse.jus.br`); a declaração está em [`sources/judiciario/federal/tse.yml`](../../sources/judiciario/federal/tse.yml). A Justiça Eleitoral integra o Poder Judiciário: por isso é a primeira fonte `judiciario/federal`.

## O que é uma candidatura

Em cada eleição, quem quer disputar um cargo registra uma **candidatura**, com cargo, UF, número de urna, partido e dados pessoais. Nas eleições gerais (a cada quatro anos) disputam-se presidente, governador, senador, deputado federal, estadual e distrital. Nas eleições municipais (também a cada quatro anos, dois anos depois) disputam-se prefeito, vice e vereador. A plataforma guarda as candidaturas de **todos os cargos**, nas eleições gerais e municipais de 1996 a 2026 (as eleições suplementares ficam no raw e fora dos marts).

## Campos que a plataforma usa

| Campo | Significado |
| --- | --- |
| `ano_eleicao`, `turno` | eleição e turno da votação |
| `sq_candidato` | sequencial do candidato **naquela eleição** (não é um identificador da pessoa) |
| `cargo`, `uf` | cargo disputado e UF (BR para cargos nacionais) |
| `numero`, `nome_urna` | número e nome na urna |
| `partido`, `partido_nome` | partido **na eleição** (a plataforma ganha o partido por período) |
| `situacao_candidatura` | situação do registro (por exemplo, deferido) |
| `dt_eleicao` | dia da votação do último turno que a candidatura disputou (`DT_ELEICAO` do arquivo; o 2º turno de 2006 de presidente vem do arquivo de votação) |
| `uf_nascimento`, `grau_instrucao`, `estado_civil`, `ocupacao`, `nome_social`, `coligacao`, `federacao` | o que o candidato **declara** no registro; `app_pessoas` usa isso para quem não está no cadastro da Câmara ou do Senado (ADR 0029) |
| `foto_caminho` | foto oficial do candidato, extraída do pacote do TSE pelo comando `fotos` |
| `resultado` | eleito por quociente partidário (QP), eleito por média, suplente, não eleito; vazio quando a fonte marca `#NULO#` |

## Marcadores de "sem valor"

Os arquivos do TSE escrevem `#NULO#` (campo sem informação) e `#NE` (não existe) onde não há valor. O raw guarda como veio, e do staging em diante todo texto dos arquivos do TSE passa por `tse_source`, que troca esses marcadores por vazio. Um teste (`test_the_tse_markers_for_no_value_never_reach_the_staging_tables`) confere que nenhuma tabela de staging do TSE os mantém.

## O que fica de fora, de propósito

CPF, título de eleitor, e-mail, cor ou raça e o nome de doadores e fornecedores **nunca** entram (a declaração da fonte não os lista). O nome social entra porque o candidato o declara (ADR 0029). Bens declarados, receitas e despesas de campanha, votos por município e zona e as fotos dos pacotes de cada UF **são carregados**; ainda não entram redes sociais, certidões criminais, e as fotos e a prestação de contas das eleições municipais (issues 150 e 177).

## Como a candidatura chega à pessoa

O TSE não tem identificador da pessoa entre eleições. A plataforma liga a candidatura a uma pessoa (deputado, senador ou qualquer eleito, ADR 0031) quando **nome civil e data de nascimento são iguais e únicos** nas duas fontes ([ADR 0013](../05-decisoes/0013-tse-ligacao-por-nome-civil-e-nascimento.md)). Candidatura que não passa na regra (homônimo, nome grafado diferente, nascimento ausente) fica sem vínculo, e o teste `eleitos_federais_sem_vinculo` mede quantos eleitos ao Congresso ficaram de fora.
