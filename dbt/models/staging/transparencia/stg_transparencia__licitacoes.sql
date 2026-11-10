-- Licitações do governo federal (SIASG), uma por linha, de 2022-11 em diante. Valor com as quatro casas que a fonte publica.
with base as (

select
    c_digo_ug || '-' || c_digo_modalidade_compra || '-' || n_mero_licita_o as id_licitacao,
    n_mero_licita_o as numero_licitacao,
    c_digo_ug as cd_ug,
    nome_ug as ug,
    c_digo_modalidade_compra as cd_modalidade,
    modalidade_compra as modalidade,
    n_mero_processo as numero_processo,
    mascarar_dado_pessoal(objeto, 'cpf') as objeto,
    situa_o_licita_o as situacao,
    c_digo_rg_o_superior as cd_orgao_superior,
    nome_rg_o_superior as orgao_superior,
    c_digo_rg_o as cd_orgao,
    nome_rg_o as orgao,
    uf as uf,
    munic_pio as municipio,
    try_strptime(data_resultado_compra, '%d/%m/%Y')::date as dt_resultado,
    try_strptime(data_abertura, '%d/%m/%Y')::date as dt_abertura,
    try_cast(replace(valor_licita_o, ',', '.') as decimal(18, 4)) as valor,
    _source_file_id as id_captura

from {{ source('transparencia', 'licitacoes') }}

)

{{ colunas_auditoria('base') }}
