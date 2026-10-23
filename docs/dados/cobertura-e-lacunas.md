# Cobertura e lacunas

Para quem quer saber **o que o banco tem hoje, o que a Câmara ainda não entrega ao projeto e o que precisa vir de outras fontes**. Responde a três perguntas: o que vem da Câmara, o que falta dela, e de onde viria o resto. O catálogo das fontes (`fontes-de-dados.md`) diz o que cada fonte oferece; este documento diz o que já foi carregado e o que sobra.

Os números abaixo são da carga histórica de 21/10/2026 (Câmara: `run --historical --from-year 2000`; Senado: `run --historical --from-year 1999 --source senado`). Eles mudam a cada carga; a página `/qualidade` do explorador mostra os atuais.

## Números da carga de 21/10/2026

| Medida | Valor |
| --- | --- |
| Pessoas (Câmara) | 7.889 (887 só aparecem nos votos, sem cadastro) |
| Proposições (Câmara) | 885.777 |
| Votações (Câmara) | 190.401, de 10/01/2000 a 15/10/2026 |
| Votações sem nenhum voto individual (simbólicas ou sem registro) | 184.362 |
| Votos individuais (Câmara) | 1.927.167 |
| Proposições sem situação atual | 489.694 |
| Pessoas sem foto | 5.682 |
| Autorias de pessoas em proposições não carregadas | 11.257 |
| Ligações votação-proposição de proposições não carregadas | 6.158 |
| Legislaturas, partidos | 58, 104 |
| Órgãos, participações em órgãos | 3.883, 94.616 |
| Frentes parlamentares, participações em frentes | 1.443, 262.014 |
| Participações em órgãos de órgão ausente da lista de órgãos da fonte | 6.409 (129 órgãos, como o Congresso Nacional e comissões especiais) |
| Participações em frentes sem deputado identificado pela fonte | 256 (coordenações antigas) |
| Pessoas, votações, votos e matérias do **Senado** | 864, 3.389 (de 1999 a 2026), 273.094 e 2.738 |
| Mandatos (votos observados) do Senado | 989 |
| Tramitação da Câmara (amostra por item: os 300 mais recentes dos 96.134 alvos) | 300 proposições, 338 andamentos |
| Processos do Senado (amostra por item: 300 das 2.738 matérias votadas) | 300 processos, 75 normas geradas |
| Pessoas hoje (depois da fusão deputado e senador) | 8.535, das quais 218 estão nas duas casas |
| Candidaturas ao Congresso no TSE (eleições gerais de 1998 a 2026) | 53.626 no staging; 6.709 ligadas a uma pessoa; 3.456 eleitas ligadas (1.900 pessoas) |
| Detalhe de senadores (nascimento, naturalidade, foto) | 842 de 843 buscados (779 com nascimento, 472 com foto) |
| Testes do dbt do tipo erro que falharam | 0 |

## 1. O que a Câmara entrega e o projeto já usa

| Dado | Fonte | Cobertura carregada |
| --- | --- | --- |
| Cadastro de deputados (nome, nome civil, sexo, nascimento, redes, site) | `deputados` | todos os deputados do arquivo, de todas as legislaturas |
| Profissões e ocupações declaradas | `deputadosProfissoes`, `deputadosOcupacoes` | arquivo completo |
| Proposições e situação atual | `proposicoes` | arquivos de 2000 a 2026 (cada arquivo traz proposições com datas de apresentação de vários anos; a regra de inclusão da fonte não foi confirmada) |
| Autoria de proposições | `proposicoesAutores` | mesmos anos |
| Votações (resultado e totais oficiais) | `votacoes` | 2000 a 2026 |
| Voto de cada deputado, com partido e UF na data | `votacoesVotos` | 2001 a 2026 |
| Orientação de bancada | `votacoesOrientacoes` | 2003 a 2026 |
| Proposições afetadas e objeto de cada votação | `votacoesProposicoes`, `votacoesObjetos` | 2000 a 2026 |
| Foto | arquivos de votos e de frentes (`deputado_urlFoto`) | quem votou ou esteve em frente |
| Legislaturas (datas oficiais) | `legislaturas` | todas |
| Partidos | `partidos` | todos |
| Órgãos e composição | `orgaos`, `orgaosDeputados` | todos os órgãos; composição das legislaturas 51 a 57 |
| Frentes parlamentares e participantes | `frentes`, `frentesDeputados` | arquivos completos |

## 2. O que a Câmara publica e o projeto ainda não carrega

| Dado | Por que importa | Observação |
| --- | --- | --- |
| Proposições anteriores a 2000 | histórico de decisões | a fonte cobre só alguns tipos antes de 2001; decidir o que mostrar |
| Mesas diretoras (`legislaturasMesas`) | quem presidiu a Casa | já coberta em parte pela composição do órgão `MESA` |
| Eventos e presenças | presença em sessões | volume grande; fora do primeiro entregável |
| Tramitação detalhada (histórico de situações) | hoje só há a **última** situação | exige o conjunto de tramitações ou a API |
| Temas e ementa detalhada | classificação por assunto | conjunto de temas da Câmara |
| Cota parlamentar (CEAP) | gastos | traz CPF e CNPJ de fornecedores: só entra com a minimização definida (o contrato recusa CPF) |
| Texto integral das proposições | leitura e resumo | links existem em `url_inteiro_teor`; o texto não é baixado |
| Início e fim do mandato **de cada pessoa** | mandato exato, com suplentes | a Câmara não publica em lote; o mart traz as datas oficiais da **legislatura** e os votos observados |

## Senado Federal: o que entra e o que falta

| Dado | Fonte | Cobertura carregada |
| --- | --- | --- |
| Senadores (nome, nome civil, sexo) e mandatos | `senadores` (por legislatura, 51 a 57) | todas as legislaturas desde 1999; mandatos e exercícios ficam no raw (`senadores__mandatos_mandato`) |
| Votações em plenário e voto de cada senador | `votacoes` (por ano) | 1999 a 2026 |
| Matérias votadas (sigla, ementa, apresentação, página oficial) | dentro das votações | só as que foram votadas |

Lacunas conhecidas, medidas ou registradas:

- **2015 e 2016 têm quase nenhuma votação** (17 e 13, contra cerca de 120 por ano nos demais). É o que a fonte devolve; a plataforma não completa.
- **Votação secreta** (1.782 das 3.389 votações e 96.075 dos 273.094 votos): a fonte não informa a escolha; o voto fica como `Votou`. `marts.votacoes.votacao_secreta` marca essas votações.
- **Totais de Sim, Não e Abstenção** vêm vazios em parte das votações antigas. O teste `votacoes_com_total_sim_divergente` compara o total oficial com a contagem dos votos individuais, deixando de fora a votação secreta (não há Sim a contar): 13 votações, todas da Câmara.
- **Sem nascimento, foto e redes** dos senadores: o arquivo de legislatura não as traz.
- **Sem autoria nem situação das matérias**: exigem uma chamada por matéria; `autorias` e `situacao` ficam vazios para o Senado, e `pessoas.qtd_propostas` é vazio (não zero) para senadores.
- **Mandatos oficiais** (titular, suplente, períodos de exercício, causas de afastamento) estão no raw, mas ainda não nos marts: `marts.mandatos` do Senado vem dos votos observados, como na Câmara.
- **Quem foi deputado e senador tem duas chaves de pessoa**: a regra conservadora liga só por identificador oficial da própria fonte, nunca por nome.

## Datasets por item (amostra)

Tramitação (Câmara) e processo (Senado) vêm por item, uma chamada para cada um, e **só rodam sob pedido** (`--foreach N`). Até a carga total ser pedida, o banco tem uma amostra dos itens mais recentes:

- **Câmara, tramitação:** só proposições que podem virar norma (PL, PLP, PEC, MPV, PDL, PLV, PLN e PRC: 96.134). Estão buscadas 300; o teste `proposicoes_alvo_sem_tramitacao` mede as que faltam, e `plataforma coverage` mostra o quadro por dataset. A fonte não tem a norma resultante nesse endpoint: `normas_geradas` vem só do Senado por enquanto.
- **Senado, processo:** estão buscados 300 das 2.738 matérias votadas. Em metade das respostas (150) a fonte não informa `situacaoAtual`; fica vazia (nada é inferido). A autoria está no raw (`processos__autoria_iniciativa`) e o corpo completo no landing, mas ainda não nos marts, para não publicar contagens parciais por senador. A tramitação do Senado (`autuacoes`) está só no landing.
- **Auditoria:** `plataforma verify` confere os hashes de todos os arquivos do landing e das respostas dentro dos lotes (landing íntegro na última conferência).

## TSE: candidaturas e ligação entre fontes

| Dado | Fonte | Cobertura carregada |
| --- | --- | --- |
| Candidaturas a deputado federal e senador (com suplentes), com partido, situação e resultado | `candidaturas` (um pacote por eleição) | eleições gerais de 1998, 2002, 2006, 2010, 2014, 2018, 2022 e 2026 |

- **Ligação** por nome civil e nascimento iguais e únicos ([ADR 0013](../adr/0013-tse-ligacao-por-nome-civil-e-nascimento.md)): 6.709 candidaturas ligadas. As demais (candidatos de fora do Congresso e quem não foi eleito) ficam no staging.
- **Eleitos sem vínculo:** 363 candidaturas marcadas como eleitas não foram ligadas (teste `eleitos_federais_sem_vinculo`): nome civil diferente entre as fontes, nascimento ausente ou homônimo. A curadoria manual resolve.
- **Nascimento ausente:** 972 pessoas sem data de nascimento (sobretudo senadores sem o detalhe, o que impede a ligação por esta regra). Uma busca do detalhe que falhou (503) é repetida na próxima execução com `--foreach`.
- **Ambiguidade:** o teste `pessoas_ambiguas_entre_fontes` mede nome civil e nascimento repetidos dentro de uma fonte.
- **Resultado da eleição de 2026:** vem como a fonte informa na data da carga; uma eleição recente pode ter resultado ainda não consolidado.
- **Ainda não carregados:** bens declarados, redes sociais, fotos, certidões, coligações, vagas e votação por candidato.

## 3. O que a Câmara **não** tem e precisa vir de outra instância

| Necessidade | Fonte provável | Por que a Câmara não basta |
| --- | --- | --- |
| Senadores, votos e matérias do Senado | Senado Federal, dados abertos | outra casa legislativa |
| Presidente, vice e ministros | TSE (candidaturas e eleitos), Planalto, DOU | pertencem ao Executivo |
| Candidaturas, eleições e resultados | TSE | a Câmara só conhece quem tomou posse |
| Filiação partidária por período | TSE | a Câmara só informa o partido **na data do voto** |
| Lei, decreto ou medida provisória que resultou da proposição | Diário Oficial da União, LexML | a Câmara termina no trâmite; a norma publicada é outro documento |
| Sanção, veto e derrubada de veto | Senado/Congresso, DOU | acontecem depois da votação na Câmara |
| Emendas parlamentares e dinheiro público | Portal da Transparência, TCU | outro assunto |
| Município de São Paulo | Câmara Municipal, Querido Diário | outro ente |
| Decisões anteriores às séries digitais | curadoria manual, rotulada | não há dado estruturado |

## 4. Limitações do carregamento atual

- **Foto só para quem votou ou esteve em frente parlamentar.** O cadastro não traz foto; ela vem dos arquivos de votos e de frentes. Quem não aparece neles fica "sem foto"; o teste `pessoas_sem_foto` mede a lacuna.
- **Mandato por votos observados.** Início e fim do mandato de cada pessoa ficam vazios, porque a fonte não os publica em lote (suplentes entram e saem no meio da legislatura). O mart traz, ao lado, as datas oficiais da legislatura (`legislatura_inicio`, `legislatura_fim`), que **não** são as do mandato (ver [identidade de pessoas](identidade-de-pessoas.md)).
- **Órgãos citados e ausentes da lista de órgãos.** A composição cita 129 órgãos (como o Congresso Nacional e comissões especiais) que `orgaos.csv` não lista. As participações ficam, com a sigla informada na própria linha, e o teste de relação do dbt mede a lacuna.
- **Participações em frentes sem deputado.** 256 linhas de coordenação antiga não identificam o deputado; ficam no staging e saem dos marts.
- **Linhas repetidas com `dataFim` diferente.** Na composição de órgãos, a fonte traz às vezes a mesma participação duas vezes, uma aberta e outra encerrada. As duas são mantidas (o raw identifica a linha pelo conteúdo, `_row_hash`); quem consome deve considerar a encerrada.
- **Referências a proposições de anos não carregados.** Votações e autorias podem citar proposições de anos que não foram baixados. Elas aparecem como "ano ainda não carregado", com o link para a ficha oficial, sem inventar dados. Testes `autoria_de_proposicao_nao_carregada` e `votacao_de_proposicao_nao_carregada` contam os casos.
- **Muitas proposições sem situação.** Nos arquivos da Câmara, uma parte grande das proposições vem sem a última situação. A página mostra o campo vazio.
- **Divergência entre fontes oficiais.** A data de falecimento de um deputado consta no arquivo em lote e não na API de detalhe. As duas fontes são oficiais; o projeto usa o arquivo em lote e registra a divergência.
- **O `merge` do dlt não apaga.** Se a Câmara remover uma linha de um arquivo, o raw mantém a linha antiga. O landing guarda os dois arquivos, então o caso é detectável; falta o teste que o aponte.
- **Siglas em ementas.** A lista de siglas para preservar a caixa é aprendida de todas as ementas de caixa mista carregadas (modelo `int_siglas_em_ementas_extraidas`, mínimo de 3 ocorrências). Uma sigla que só apareça em ementas de caixa alta pode ser minusculizada.

## 5. Onde estão os números atuais

| Pergunta | Onde ver |
| --- | --- |
| Quantas linhas há em cada tabela e quanto de cada coluna está preenchido | `/qualidade` do explorador |
| Quais testes de dados falharam ou mediram lacuna | `/qualidade`, seção "Testes de dados" |
| Há quanto tempo cada arquivo foi verificado | `/qualidade`, seção "Frescor das capturas" |
| Quais valores existem em colunas como `voto` e `situacao` | `/qualidade`, "Valores de colunas categóricas" |
