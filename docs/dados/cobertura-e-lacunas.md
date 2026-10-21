# Cobertura e lacunas

Para quem quer saber **o que o banco tem hoje, o que a Câmara ainda não entrega ao projeto e o que precisa vir de outras fontes**. Responde a três perguntas: o que vem da Câmara, o que falta dela, e de onde viria o resto. O catálogo das fontes (`fontes-de-dados.md`) diz o que cada fonte oferece; este documento diz o que já foi carregado e o que sobra.

Os números abaixo são da carga histórica de 21/10/2026 (`run --historical --from-year 2000`). Eles mudam a cada carga; a página `/qualidade` do explorador mostra os atuais.

## Números da carga de 21/10/2026

| Medida | Valor |
| --- | --- |
| Pessoas | 7.889 (887 só aparecem nos votos, sem cadastro) |
| Proposições | 885.735 |
| Votações | 190.401, de 10/01/2000 a 15/10/2026 |
| Votações sem nenhum voto individual (simbólicas ou sem registro) | 184.347 |
| Votos individuais | 1.927.167 |
| Proposições sem situação atual | 489.787 |
| Pessoas sem foto | 5.682 |
| Autorias de pessoas em proposições não carregadas | 11.226 |
| Ligações votação-proposição de proposições não carregadas | 6.010 |
| Legislaturas, partidos | 58, 104 |
| Órgãos, participações em órgãos | 3.883, 94.616 |
| Frentes parlamentares, participações em frentes | 1.443, 262.014 |
| Participações em órgãos de órgão ausente da lista de órgãos da fonte | 6.409 (129 órgãos, como o Congresso Nacional e comissões especiais) |
| Participações em frentes sem deputado identificado pela fonte | 256 (coordenações antigas) |
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
