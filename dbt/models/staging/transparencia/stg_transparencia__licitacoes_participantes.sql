-- Participantes dos itens das licitações do governo federal. Participante entra mascarado: pode ser pessoa física, com CPF completo no raw.
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
    mascarar_dado_pessoal(descri_o_item_compra, 'cpf') as item,
    mascarar_dado_pessoal(c_digo_participante, 'favorecido') as cd_participante,
    mascarar_dado_pessoal(nome_participante, 'favorecido') as participante,
    case upper(flag_vencedor) when 'SIM' then true when 'NÃO' then false end as fl_vencedor,
    _source_file_id as id_captura

from {{ source('transparencia', 'licitacoes_participantes') }}

)

{{ colunas_auditoria('base') }}
