# Renomeação dos marts

Para quem consome os dados (aplicações e pessoas que auditam): o nome antigo e o novo de cada tabela e coluna dos marts. Regra em [convenção de nomes](../engenharia/convencao-de-nomes.md); decisão no [ADR 0022](../adr/0022-convencao-de-nomes-e-descricoes.md).

**Estado: proposta para aprovação.** Ainda não aplicada: os marts continuam com os nomes antigos.

## Tabelas

| Antes | Depois |
| --- | --- |
| `bens_de_candidatos` | `candidaturas_bens` |
| `votos_de_candidatos` | `candidaturas_votos` |
| `membros_de_frentes` | `frentes_membros` |
| `exercicios` | `mandatos_exercicios` |
| `membros_de_orgaos` | `orgaos_membros` |
| `linhagem_de_partidos` | `partidos_linhagem` |
| `fusoes_de_pessoas` | `pessoas_fusoes` |
| `ocupacoes` | `pessoas_ocupacoes` |
| `autorias` | `proposicoes_autorias` |
| `tramitacoes` | `proposicoes_tramitacoes` |
| `dispositivos_vetados` | `vetos_dispositivos` |
| `votos_em_vetos` | `vetos_votos` |
| `votos` | `votacoes_votos` |

Sem mudança (19): `candidaturas`, `constituicao_alteracoes`, `constituicao_dispositivos`, `emendas`, `emendas_convenios`, `emendas_favorecidos`, `frentes`, `legislaturas`, `mandatos`, `normas`, `normas_geradas`, `normas_publicacoes`, `normas_relacoes`, `orgaos`, `partidos`, `pessoas`, `proposicoes`, `vetos`, `votacoes`.

## Colunas

Só as colunas que mudam; as demais ficam como estão.

### `candidaturas`

| Antes | Depois |
| --- | --- |
| `candidatura_id` | `id_candidatura` |
| `capturado_em` | `dt_captura` |

12 colunas sem mudança.

### `candidaturas_bens` (antes `bens_de_candidatos`)

| Antes | Depois |
| --- | --- |
| `candidatura_id` | `id_candidatura` |
| `atualizado_em` | `dt_atualizacao` |
| `capturado_em` | `dt_captura` |

7 colunas sem mudança.

### `candidaturas_votos` (antes `votos_de_candidatos`)

| Antes | Depois |
| --- | --- |
| `candidatura_id` | `id_candidatura` |
| `capturado_em` | `dt_captura` |

9 colunas sem mudança.

### `constituicao_dispositivos`

| Antes | Depois |
| --- | --- |
| `capturado_em` | `dt_captura` |

14 colunas sem mudança.

### `emendas`

| Antes | Depois |
| --- | --- |
| `capturado_em` | `dt_captura` |

25 colunas sem mudança.

### `emendas_convenios`

| Antes | Depois |
| --- | --- |
| `publicado_em` | `dt_publicacao` |
| `capturado_em` | `dt_captura` |

10 colunas sem mudança.

### `emendas_favorecidos`

| Antes | Depois |
| --- | --- |
| `contem_dado_pessoal` | `fl_contem_dado_pessoal` |
| `capturado_em` | `dt_captura` |

15 colunas sem mudança.

### `frentes`

| Antes | Depois |
| --- | --- |
| `frente_id` | `id_frente` |
| `criada_em` | `dt_criacao` |
| `legislatura_id` | `id_legislatura` |

4 colunas sem mudança.

### `frentes_membros` (antes `membros_de_frentes`)

| Antes | Depois |
| --- | --- |
| `frente_id` | `id_frente` |
| `legislatura_id` | `id_legislatura` |
| `inicio` | `dt_inicio` |
| `fim` | `dt_fim` |

3 colunas sem mudança.

### `legislaturas`

| Antes | Depois |
| --- | --- |
| `legislatura_id` | `id_legislatura` |
| `inicio` | `dt_inicio` |
| `fim` | `dt_fim` |

2 colunas sem mudança.

### `mandatos`

| Antes | Depois |
| --- | --- |
| `legislatura_id` | `id_legislatura` |
| `inicio` | `dt_inicio` |
| `fim` | `dt_fim` |
| `primeiro_voto_observado_em` | `dt_primeiro_voto_observado` |
| `ultimo_voto_observado_em` | `dt_ultimo_voto_observado` |
| `legislatura_inicio` | `dt_legislatura_inicio` |
| `legislatura_fim` | `dt_legislatura_fim` |

6 colunas sem mudança.

### `mandatos_exercicios` (antes `exercicios`)

| Antes | Depois |
| --- | --- |
| `mandato_id` | `id_mandato` |
| `exercicio_id` | `id_exercicio` |
| `mandato_inicio` | `dt_mandato_inicio` |
| `mandato_fim` | `dt_mandato_fim` |
| `inicio` | `dt_inicio` |
| `fim` | `dt_fim` |

6 colunas sem mudança.

### `normas`

| Antes | Depois |
| --- | --- |
| `norma_id` | `id_norma` |
| `assinada_em` | `dt_assinatura` |
| `capturado_em` | `dt_captura` |

11 colunas sem mudança.

### `normas_geradas`

| Antes | Depois |
| --- | --- |
| `proposicao_id` | `id_proposicao` |
| `norma_id` | `id_norma` |
| `assinada_em` | `dt_assinatura` |
| `publicada_em` | `dt_publicacao` |
| `capturado_em` | `dt_captura` |

6 colunas sem mudança.

### `normas_publicacoes`

| Antes | Depois |
| --- | --- |
| `norma_id` | `id_norma` |
| `publicacao_id` | `id_publicacao` |
| `publicada_em` | `dt_publicacao` |
| `tem_texto` | `fl_tem_texto` |
| `capturado_em` | `dt_captura` |

5 colunas sem mudança.

### `normas_relacoes`

| Antes | Depois |
| --- | --- |
| `norma_id` | `id_norma` |
| `norma_posterior_id` | `id_norma_posterior` |
| `norma_posterior_assinada_em` | `dt_norma_posterior_assinatura` |
| `publicada_em` | `dt_publicacao` |
| `capturado_em` | `dt_captura` |

4 colunas sem mudança.

### `orgaos`

| Antes | Depois |
| --- | --- |
| `orgao_id` | `id_orgao` |
| `inicio` | `dt_inicio` |
| `instalado_em` | `dt_instalacao` |
| `fim` | `dt_fim` |

8 colunas sem mudança.

### `orgaos_membros` (antes `membros_de_orgaos`)

| Antes | Depois |
| --- | --- |
| `orgao_id` | `id_orgao` |
| `inicio` | `dt_inicio` |
| `fim` | `dt_fim` |

6 colunas sem mudança.

### `partidos`

| Antes | Depois |
| --- | --- |
| `partido_id` | `id_partido` |

3 colunas sem mudança.

### `partidos_linhagem` (antes `linhagem_de_partidos`)

| Antes | Depois |
| --- | --- |
| `aprovado_em` | `dt_aprovacao` |

6 colunas sem mudança.

### `pessoas`

| Antes | Depois |
| --- | --- |
| `data_nascimento` | `dt_nascimento` |
| `data_falecimento` | `dt_falecimento` |
| `ultimo_voto_em` | `dt_ultimo_voto` |
| `capturado_em` | `dt_captura` |

20 colunas sem mudança.

### `pessoas_fusoes` (antes `fusoes_de_pessoas`)

| Antes | Depois |
| --- | --- |
| `fundida_em` | `dt_fusao` |

3 colunas sem mudança.

### `proposicoes`

| Antes | Depois |
| --- | --- |
| `proposicao_id` | `id_proposicao` |
| `apresentada_em` | `dt_apresentacao` |
| `ultimo_status_em` | `dt_ultimo_status` |
| `capturado_em` | `dt_captura` |

7 colunas sem mudança.

### `proposicoes_autorias` (antes `autorias`)

| Antes | Depois |
| --- | --- |
| `proposicao_id` | `id_proposicao` |

8 colunas sem mudança.

### `proposicoes_tramitacoes` (antes `tramitacoes`)

| Antes | Depois |
| --- | --- |
| `proposicao_id` | `id_proposicao` |
| `registrada_em` | `dt_registro` |
| `capturado_em` | `dt_captura` |

7 colunas sem mudança.

### `vetos`

| Antes | Depois |
| --- | --- |
| `veto_id` | `id_veto` |
| `materia_veto_id` | `id_materia_veto` |
| `materia_vetada_id` | `id_materia_vetada` |
| `norma_id` | `id_norma` |
| `veto_total` | `fl_veto_total` |
| `recebido_em` | `dt_recebimento` |
| `publicado_em` | `dt_publicacao` |
| `sobrestado_em` | `dt_sobrestamento` |
| `sobrestando_pauta` | `fl_sobrestando_pauta` |
| `em_tramitacao` | `fl_em_tramitacao` |
| `capturado_em` | `dt_captura` |

14 colunas sem mudança.

### `vetos_dispositivos` (antes `dispositivos_vetados`)

| Antes | Depois |
| --- | --- |
| `dispositivo_id` | `id_dispositivo` |
| `materia_veto_id` | `id_materia_veto` |
| `veto_id` | `id_veto` |
| `possui_votos` | `fl_possui_votos` |
| `sessao_em` | `dt_sessao` |
| `capturado_em` | `dt_captura` |

7 colunas sem mudança.

### `vetos_votos` (antes `votos_em_vetos`)

| Antes | Depois |
| --- | --- |
| `dispositivo_id` | `id_dispositivo` |
| `capturado_em` | `dt_captura` |

7 colunas sem mudança.

### `votacoes`

| Antes | Depois |
| --- | --- |
| `votacao_id` | `id_votacao` |
| `data` | `dt_votacao` |
| `votacao_secreta` | `fl_votacao_secreta` |
| `capturado_em` | `dt_captura` |

8 colunas sem mudança.

### `votacoes_votos` (antes `votos`)

| Antes | Depois |
| --- | --- |
| `votacao_id` | `id_votacao` |
| `votou_em` | `dt_voto` |

5 colunas sem mudança.

## Decisões em aberto

- **Códigos da fonte** (`emendas.emenda_codigo`, `emendas.autor_codigo`, `emendas.programa_codigo`, `emendas.acao_codigo`, `emendas_convenios.emenda_codigo`, `emendas_favorecidos.emenda_codigo`, `emendas_favorecidos.autor_codigo`, `emendas_favorecidos.favorecido_codigo`): ficam como estão até haver decisão. Proposta: prefixo `cd_` (`cd_emenda`, `cd_autor`...), por serem códigos da fonte, e não chaves nossas.
- **`emendas`:** continua com o nome, porque o tema é a emenda parlamentar orçamentária; `constituicao_alteracoes` cobre as emendas constitucionais.
- **`orgaos`:** continua com o nome; a descrição diz que são órgãos legislativos (Câmara e Senado).
- **`normas_geradas`:** já tem o tema na frente (normas) e continua; a descrição diz que são normas geradas por matérias do Senado.
- **Colunas `fonte`, `fonte_url` e `fontes`:** não têm prefixo de tipo e continuam como estão, por serem o contrato de proveniência do projeto.
