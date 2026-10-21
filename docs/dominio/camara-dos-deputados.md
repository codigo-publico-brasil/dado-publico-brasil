# Domínio: a Câmara dos Deputados e como ela vira dado

Este documento explica **o que é a Câmara, o que ela faz e quais são as regras de negócio** por trás de cada campo que o projeto guarda. Quem entende a regra entende por que o dado tem a forma que tem (por exemplo, por que uma proposição tem dezenas de "autores", ou por que há votações sem voto individual).

> **Atenção.** Este texto resume regras do Regimento Interno e da Constituição para dar contexto ao dado. Pontos marcados com **(confirmar)** são interpretações do que aparece nos arquivos e devem ser conferidos na fonte oficial antes de qualquer uso público. O que vale para o projeto é sempre o texto oficial e o dado capturado.

## O Congresso e as suas duas casas

O Poder Legislativo federal é o **Congresso Nacional**, formado por duas casas:

| | Câmara dos Deputados | Senado Federal |
| --- | --- | --- |
| Quem representa | o povo | os estados e o Distrito Federal |
| Membros | 513 deputados federais | 81 senadores (3 por estado e pelo DF) |
| Mandato | 4 anos | 8 anos |
| Eleição | proporcional (partidos e votos) | majoritária (mais votado) |

Cada período de 4 anos é uma **legislatura**, numerada: a 57ª legislatura vai de 2023 a 2027, a 56ª de 2019 a 2023. No dado, `legislatura` é esse número.

O que o Congresso faz: **legislar** (aprovar leis e emendas à Constituição), **fiscalizar** o Executivo (requerimentos de informação, comissões parlamentares de inquérito, convocação de ministros) e **representar** a população. A Câmara tem competências próprias, como autorizar a abertura de processo contra o presidente da República.

## Quem pode propor o quê

Qualquer deputado pode apresentar proposições. Também propõem: comissões, a Mesa, o presidente da República, o Supremo Tribunal Federal, tribunais superiores e, por iniciativa popular, cidadãos (com assinaturas). Projetos do Executivo, do Judiciário e de iniciativa popular **começam pela Câmara**.

### Tipos de proposição que aparecem nos dados

O campo `sigla_tipo` (e `descricao_tipo`) diz o que a proposição é. Os principais:

| Sigla | O que é | Observação |
| --- | --- | --- |
| **PL** | Projeto de lei | Vira lei ordinária se aprovado pelas duas casas e sancionado |
| **PLP** | Projeto de lei complementar | Exige maioria absoluta; regula pontos que a Constituição manda detalhar |
| **PEC** | Proposta de emenda à Constituição | Muda a Constituição; exige apoio de pelo menos 1/3 dos deputados para ser apresentada (171) e 3/5 dos votos em dois turnos |
| **PDL** | Projeto de decreto legislativo | Matérias de competência exclusiva do Congresso, sem sanção do presidente |
| **PRC** | Projeto de resolução | Assuntos internos da Câmara |
| **MPV** | Medida provisória | Vem do presidente; tem força de lei por prazo limitado e precisa ser votada pelo Congresso |
| **REQ** | Requerimento | Pedido (urgência, audiência pública, criação de frente parlamentar, informação a ministério) |
| **EMC / EMP** e similares | Emendas | Alterações propostas a outra proposição, em comissão ou em plenário **(confirmar o significado exato de cada sigla na tabela oficial de tipos)** |
| **PRL** | Parecer de relator em comissão | Documento da tramitação, não um projeto |
| **RDF** | Redação final | Versão final do texto aprovado, antes de seguir |

Consequência para o dado: **a maior parte das "propostas" de um deputado é requerimento ou emenda**, não projeto de lei. Contar "quantos projetos o deputado propôs" exige filtrar por tipo, e o projeto precisa dizer qual filtro usou. A metodologia ([metodologia-v0](../../../quem-decidiu/docs/produto/metodologia-v0.md)) define "propôs".

## Autoria, assinatura e "proponente"

Uma proposição pode ter **vários autores**. A fonte lista uma linha por autor, com `ordemAssinatura` (a posição na lista) e `proponente`:

- Nos projetos de lei comuns, costuma haver um autor e, às vezes, coautores.
- Em **PEC**, são necessárias 171 assinaturas só para apresentar. Por isso uma PEC aparece com 170 a 190 "autores", quase todos **apoiadores** que assinaram, e poucos marcados como proponentes. Algo parecido vale para requerimento de CPI.
- O autor pode não ser deputado: pode ser uma **comissão**, o **Senado**, um **órgão do Executivo** ou a **sociedade civil**. No dado, `id_pessoa` fica vazio nesses casos e `tipo_autor` diz o que é.

Consequência para o dado: "autoria" não equivale a "responsabilidade pela iniciativa". Exibir "1º de 185" ao lado do nome diferencia quem lidera de quem apoia, e a página não deve tratar as duas situações como iguais.

## O caminho de uma proposição (tramitação)

1. **Apresentação:** a proposição é protocolada e recebe número e ano (PL 1234/2025).
2. **Despacho:** o presidente da Câmara a encaminha às comissões que devem analisá-la e define o regime de tramitação (ordinário, urgência, prioridade).
3. **Comissões:** designa-se um **relator**, que dá o parecer; a comissão vota. Alguns projetos são aprovados ali de forma **conclusiva**, sem passar pelo plenário.
4. **Plenário:** quando vai ao plenário, é votada pelos deputados.
5. **Outra casa:** se aprovada, segue ao Senado (ou volta à Câmara, se começou lá), que pode aprovar, rejeitar ou emendar.
6. **Sanção ou veto:** o presidente sanciona (vira lei) ou veta. O Congresso pode derrubar o veto.
7. **Publicação** no Diário Oficial da União (fonte futura do projeto).

A qualquer momento a proposição pode ser **arquivada**, **apensada** (anexada a outra de tema semelhante, e passa a tramitar em conjunto) ou perder o objeto.

### Situação atual

O campo `situacao` é a **última situação registrada**, por exemplo "Aguardando Designação de Relator(a)", "Pronta para Pauta", "Tramitando em Conjunto", "Arquivada", "Tramitação Finalizada" ou "Aguardando Apreciação pelo Senado Federal". Duas regras de uso:

- É o **estado em um momento**, com data (`data_ultimo_status`) e órgão (`orgao_ultimo_status`). A página sempre mostra a data.
- **Não é nota nem julgamento.** "Arquivada" ou "Aguardando Parecer" descreve o trâmite, não o mérito da proposta, e o projeto não usa linguagem avaliativa.
- Nos arquivos, uma parte grande das proposições vem **sem situação**. Isso é registrado como lacuna (`proposicoes_sem_situacao`), nunca preenchido por suposição.

### Andamentos (tramitação)

A tramitação completa (cada andamento, com data, órgão, regime, situação e o texto do despacho) não existe em arquivo em lote: a plataforma a busca na API, **uma chamada por proposição**, e só das que podem virar norma: PL, PLP, PEC, MPV, PDL, PLV, PLN e PRC (requerimentos, pareceres e emendas ficam de fora). A busca roda sob pedido (`--foreach`), dos mais recentes aos mais antigos, e o resultado é o mart `tramitacoes`. Enquanto a carga é por amostra, `plataforma coverage` e o teste `proposicoes_alvo_sem_tramitacao` mostram quantas faltam. Esse endpoint não traz a norma resultante (número da lei): ela virá do Planalto e do LexML.

## Votação

Uma **votação** é um ato em que um órgão (o plenário ou uma comissão) decide sobre uma proposição ou sobre um requerimento relacionado a ela. Os campos principais: `data`, `sigla_orgao` (PLEN para o plenário), `aprovacao`, os **totais oficiais** (`votos_sim`, `votos_nao`, `votos_outros`) e a descrição.

### Modos de votar

| Modo | Como é | O que existe no dado |
| --- | --- | --- |
| **Nominal** | cada deputado registra o voto no painel eletrônico | um voto por deputado |
| **Simbólica** | o presidente da sessão pede que se levantem os que são a favor; ninguém registra voto individual | **só o resultado, sem voto individual** |
| **Secreta** | casos previstos na Constituição e no Regimento | resultado sem a identificação do voto |

Por isso o projeto mostra **"sem voto individual"** em vez de preencher: ausência de voto individual não é abstenção nem falta. O teste `votacao_sem_voto_individual` mede quantas votações estão nesse caso.

### Valores do voto

O campo `voto` traz o que a fonte registra: **Sim**, **Não**, **Abstenção**, **Obstrução** e **Artigo 17**. Alguns pontos:

- **Obstrução** é uma ação parlamentar: o deputado sinaliza que não quer que a matéria seja votada. Não é um voto Sim nem Não.
- **Artigo 17** aparece quando o presidente da sessão está conduzindo os trabalhos; pelo Regimento Interno, em regra, o presidente não vota **(confirmar a regra e o artigo na fonte)**. Não é abstenção.
- Há registros com o campo vazio; ficam como a fonte os entrega e aparecem na página de qualidade.

### Partido e UF "na data"

O deputado pode **mudar de partido** durante o mandato. Cada voto traz o partido e a UF **no dia da votação** (`sigla_partido_na_data`). O projeto exibe o do dia, não o atual, porque o que importa é por qual partido a pessoa votava naquele momento.

### Orientação de bancada

Antes de votações importantes, os líderes de partidos e blocos **orientam** como a bancada deve votar (Sim, Não, Liberado, Obstrução). A fonte registra a orientação por bancada e votação (só em plenário). Votar diferente da orientação é permitido e comum; o projeto só exibe a orientação, sem tratar o desvio como julgamento.

## O que a Câmara publica e como o projeto usa

| Conjunto da fonte | Conteúdo | Tabela padronizada |
| --- | --- | --- |
| `deputados` | cadastro (sem documentos pessoais no projeto) | `camara_deputado` |
| `deputadosProfissoes`, `deputadosOcupacoes` | profissões e ocupações declaradas | `camara_deputado_profissao`, `camara_deputado_ocupacao` |
| `proposicoes`, `proposicoesAutores` | proposições e autores, por ano | `camara_proposicao`, `camara_proposicao_autor` |
| `votacoes`, `votacoesVotos` | votações e votos nominais, por ano | `camara_votacao`, `camara_voto` |
| `votacoesOrientacoes` | orientação de bancada | `camara_orientacao` |
| `votacoesProposicoes`, `votacoesObjetos` | proposições afetadas e objeto de cada votação | `camara_votacao_proposicao` |

A cobertura e o que ainda não vem da Câmara estão em [cobertura-e-lacunas](../dados/cobertura-e-lacunas.md).

## Vocabulário rápido

| Termo | Significado |
| --- | --- |
| **Legislatura** | período de 4 anos, numerado (57ª = 2023 a 2027) |
| **Plenário** | reunião de todos os deputados |
| **Comissão** | grupo menor, por tema, que analisa proposições antes do plenário |
| **Relator** | deputado que dá o parecer sobre a proposição numa comissão |
| **Apensar** | anexar uma proposição a outra de tema semelhante |
| **Mesa Diretora** | comando da Casa, presidida pelo presidente da Câmara |
| **Bancada, bloco** | grupo de deputados de um partido ou de partidos que se juntam |
| **Líder** | quem representa a bancada e dá a orientação de voto |
| **Frente parlamentar** | associação suprapartidária em torno de um tema; muitos requerimentos pedem o seu registro |
| **Ementa** | resumo oficial, em uma frase, do que a proposição faz |
| **Sessão solene** | sessão de homenagem, sem votação de matéria |
