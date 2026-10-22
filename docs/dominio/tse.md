# Tribunal Superior Eleitoral: o que os dados dizem

Para quem quer entender os campos que a plataforma traz do TSE. A fonte é o portal de dados abertos (`https://dadosabertos.tse.jus.br`); a declaração está em [`sources/judiciario/federal/tse.yml`](../../sources/judiciario/federal/tse.yml). A Justiça Eleitoral integra o Poder Judiciário: por isso é a primeira fonte `judiciario/federal`.

## O que é uma candidatura

Em cada eleição, quem quer disputar um cargo registra uma **candidatura**, com cargo, UF, número de urna, partido e dados pessoais. Nas eleições gerais (a cada quatro anos) disputam-se presidente, governador, senador, deputado federal, estadual e distrital. A plataforma guarda só as candidaturas ao **Congresso**: deputado federal e senador (com os suplentes de senador).

## Campos que a plataforma usa

| Campo | Significado |
| --- | --- |
| `ano_eleicao`, `turno` | eleição e turno da votação |
| `sq_candidato` | sequencial do candidato **naquela eleição** (não é um identificador da pessoa) |
| `cargo`, `uf` | cargo disputado e UF (BR para cargos nacionais) |
| `numero`, `nome_urna` | número e nome na urna |
| `partido`, `partido_nome` | partido **na eleição** (a plataforma ganha o partido por período) |
| `situacao_candidatura` | situação do registro (por exemplo, deferido) |
| `resultado` | eleito por quociente partidário (QP), eleito por média, suplente, não eleito; vazio quando a fonte marca `#NULO#` |

## O que fica de fora, de propósito

CPF, título de eleitor, e-mail e nome social do candidato **nunca** entram (a declaração da fonte não os lista). Bens declarados, redes sociais, fotos e certidões ainda não foram carregados.

## Como a candidatura chega à pessoa

O TSE não tem identificador da pessoa entre eleições. A plataforma liga a candidatura a um deputado ou senador quando **nome civil e data de nascimento são iguais e únicos** nas duas fontes ([ADR 0013](../adr/0013-tse-ligacao-por-nome-civil-e-nascimento.md)). Candidatura que não passa na regra (homônimo, nome grafado diferente, nascimento ausente) fica sem vínculo, e o teste `eleitos_federais_sem_vinculo` mede quantos eleitos ficaram de fora.
