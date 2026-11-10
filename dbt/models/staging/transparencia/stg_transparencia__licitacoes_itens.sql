-- Itens das licitações do governo federal, com o vencedor (uma linha por item e vencedor). Vencedor entra mascarado: pode ser pessoa física, com CPF completo no raw.
with base as (

select
    c_digo_ug || '-' || c_digo_modalidade_compra || '-' || n_mero_licita_o as id_licitacao,
    n_mero_licita_o as numero_licitacao,
    c_digo_ug as cd_ug,
    nome_ug as ug,
    c_digo_modalidade_compra as cd_modalidade,
    modalidade_compra as modalidade,
    n_mero_processo as numero_processo,
    c_digo_rg_o as cd_orgao,
    nome_rg_o as orgao,
    c_digo_item_compra as cd_item,
    mascarar_dado_pessoal(descri_o, 'cpf') as item,
    try_cast(replace(quantidade_item, ',', '.') as decimal(18, 4)) as quantidade,
    try_cast(replace(valor_item, ',', '.') as decimal(18, 4)) as valor,
    mascarar_dado_pessoal(c_digo_vencedor, 'favorecido') as cd_vencedor,
    mascarar_dado_pessoal(nome_vencedor, 'favorecido') as vencedor,
    _source_file_id as id_captura

from {{ source('transparencia', 'licitacoes_itens') }}

)

{{ colunas_auditoria('base') }}
