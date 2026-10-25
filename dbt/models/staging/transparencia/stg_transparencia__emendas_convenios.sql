-- Convênios firmados com recursos de emendas: uma linha por convênio e emenda.
select
    nullif(nullif(c_digo_da_emenda, 'Sem informação'), 'S/I') as cd_emenda,
    c_digo_fun_o as cd_funcao,
    nome_fun_o as funcao,
    c_digo_subfun_o as cd_subfuncao,
    nome_subfun_o as subfuncao,
    localidade_do_gasto as localidade,
    tipo_de_emenda as tipo,
    try_strptime(data_publica_o_conv_nio, '%d/%m/%Y')::date as dt_publicacao,
    convenente,
    objeto_conv_nio as objeto,
    n_mero_conv_nio as convenio_numero,
    try_cast(replace(valor_conv_nio, ',', '.') as decimal(18, 2)) as valor,
    _source_file_id as id_captura

from {{ source('transparencia', 'emendas_convenios') }}
