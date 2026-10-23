-- Convênios firmados com recursos de emendas: uma linha por convênio e emenda.
select
    nullif(nullif(c_digo_da_emenda, 'Sem informação'), 'S/I') as emenda_codigo,
    try_cast(c_digo_fun_o as integer) as funcao_codigo,
    nome_fun_o as funcao,
    try_cast(c_digo_subfun_o as integer) as subfuncao_codigo,
    nome_subfun_o as subfuncao,
    localidade_do_gasto as localidade,
    tipo_de_emenda as tipo,
    try_strptime(data_publica_o_conv_nio, '%d/%m/%Y')::date as publicado_em,
    convenente,
    objeto_conv_nio as objeto,
    n_mero_conv_nio as convenio_numero,
    try_cast(replace(valor_conv_nio, ',', '.') as decimal(18, 2)) as valor,
    _source_file_id as source_file_id

from {{ source('transparencia', 'emendas_convenios') }}
