-- Execução da despesa federal por mês, órgão, unidade gestora, ação e natureza da despesa, com os valores empenhado, liquidado e pago. Não traz favorecido (o arquivo não o publica).
with base as (

select
    try_strptime(ano_e_m_s_do_lan_amento || '/01', '%Y/%m/%d')::date as dt_lancamento,
    c_digo_rg_o_superior as cd_orgao_superior,
    nome_rg_o_superior as orgao_superior,
    c_digo_rg_o_subordinado as cd_orgao_subordinado,
    nome_rg_o_subordinado as orgao_subordinado,
    c_digo_unidade_gestora as cd_unidade_gestora,
    nome_unidade_gestora as unidade_gestora,
    c_digo_gest_o as cd_gestao,
    nome_gest_o as gestao,
    c_digo_unidade_or_ament_ria as cd_unidade_orcamentaria,
    nome_unidade_or_ament_ria as unidade_orcamentaria,
    c_digo_fun_o as cd_funcao,
    nome_fun_o as funcao,
    c_digo_subfu_o as cd_subfuncao,
    nome_subfun_o as subfuncao,
    c_digo_programa_or_ament_rio as cd_programa_orcamentario,
    nome_programa_or_ament_rio as programa_orcamentario,
    c_digo_a_o as cd_acao,
    nome_a_o as acao,
    c_digo_plano_or_ament_rio as cd_plano_orcamentario,
    plano_or_ament_rio as plano_orcamentario,
    c_digo_programa_governo as cd_programa_governo,
    nome_programa_governo as programa_governo,
    uf as uf,
    munic_pio as municipio,
    c_digo_subt_tulo as cd_subtitulo,
    nome_subt_tulo as subtitulo,
    c_digo_localizador as cd_localizador,
    nome_localizador as localizador,
    sigla_localizador as sigla_localizador,
    descri_o_complementar_localizador as localizador_descricao,
    c_digo_autor_emenda as cd_autor_emenda,
    nome_autor_emenda as autor_emenda,
    c_digo_categoria_econ_mica as cd_categoria_economica,
    nome_categoria_econ_mica as categoria_economica,
    c_digo_grupo_de_despesa as cd_grupo_despesa,
    nome_grupo_de_despesa as grupo_despesa,
    c_digo_elemento_de_despesa as cd_elemento_despesa,
    nome_elemento_de_despesa as elemento_despesa,
    c_digo_modalidade_da_despesa as cd_modalidade_despesa,
    modalidade_da_despesa as modalidade_despesa,
    try_cast(replace(valor_empenhado_rx, ',', '.') as decimal(18, 2)) as valor_empenhado,
    try_cast(replace(valor_liquidado_rx, ',', '.') as decimal(18, 2)) as valor_liquidado,
    try_cast(replace(valor_pago_rx, ',', '.') as decimal(18, 2)) as valor_pago,
    try_cast(replace(valor_restos_a_pagar_inscritos_rx, ',', '.') as decimal(18, 2)) as valor_restos_a_pagar_inscritos,
    try_cast(replace(valor_restos_a_pagar_cancelado_rx, ',', '.') as decimal(18, 2)) as valor_restos_a_pagar_cancelados,
    try_cast(replace(valor_restos_a_pagar_pagos_rx, ',', '.') as decimal(18, 2)) as valor_restos_a_pagar_pagos,
    _source_file_id as id_captura

from {{ source('transparencia', 'despesas') }}

)

{{ colunas_auditoria('base') }}
