-- Termos aditivos dos contratos do governo federal.
with base as (

select
    c_digo_ug || '-' || n_mero_contrato as id_contrato,
    n_mero_contrato as numero_contrato,
    c_digo_rg_o_superior as cd_orgao_superior,
    nome_rg_o_superior as orgao_superior,
    c_digo_rg_o as cd_orgao,
    nome_rg_o as orgao,
    c_digo_ug as cd_ug,
    nome_ug as ug,
    n_mero_termo_aditivo as numero_termo_aditivo,
    try_strptime(data_publica_o, '%d/%m/%Y')::date as dt_publicacao,
    mascarar_dado_pessoal(objeto, 'cpf') as objeto,
    _source_file_id as id_captura

from {{ source('transparencia', 'compras_termos_aditivos') }}

)

{{ colunas_auditoria('base') }}
