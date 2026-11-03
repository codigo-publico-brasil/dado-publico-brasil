-- Itens dos contratos do governo federal.
with base as (

select
    c_digo_rg_o as cd_orgao,
    nome_rg_o as orgao,
    c_digo_ug as cd_ug,
    nome_ug as ug,
    n_mero_contrato as numero_contrato,
    c_digo_item_compra as cd_item,
    mascarar_dado_pessoal(descri_o_item_compra, 'cpf') as item,
    mascarar_dado_pessoal(descri_o_complementar_item_compra, 'cpf') as item_descricao,
    try_cast(replace(quantidade_item, ',', '.') as decimal(18, 4)) as quantidade,
    try_cast(replace(valor_item, ',', '.') as decimal(18, 2)) as valor,
    _source_file_id as id_captura

from {{ source('transparencia', 'compras_itens') }}

)

{{ colunas_auditoria('base') }}
