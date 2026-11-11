-- Empenhos relacionados às licitações do governo federal.
with base as (

select
    c_digo_ug || '-' || c_digo_modalidade_compra || '-' || n_mero_licita_o as id_licitacao,
    n_mero_licita_o as numero_licitacao,
    c_digo_ug as cd_ug,
    nome_ug as ug,
    c_digo_modalidade_compra as cd_modalidade,
    modalidade_compra as modalidade,
    n_mero_processo as numero_processo,
    c_digo_empenho as cd_empenho,
    try_strptime(data_emiss_o_empenho, '%d/%m/%Y')::date as dt_emissao,
    mascarar_dado_pessoal(observa_o_empenho, 'cpf') as observacao,
    try_cast(replace(valor_empenho_rx, ',', '.') as decimal(18, 4)) as valor,
    _source_file_id as id_captura

from {{ source('transparencia', 'licitacoes_empenhos') }}

)

{{ colunas_auditoria('base') }}
