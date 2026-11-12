-- Contratos do governo federal, um por linha, de 2022-11 em diante. Contratado (nome e código) entra mascarado: pessoa física vem com CPF completo no raw.
with base as (

select
    c_digo_ug || '-' || n_mero_do_contrato as id_contrato,
    n_mero_do_contrato as numero_contrato,
    mascarar_dado_pessoal(objeto, 'cpf') as objeto,
    fundamento_legal as fundamento_legal,
    modalidade_compra as modalidade_compra,
    situa_o_contrato as situacao,
    c_digo_rg_o_superior as cd_orgao_superior,
    nome_rg_o_superior as orgao_superior,
    c_digo_rg_o as cd_orgao,
    nome_rg_o as orgao,
    c_digo_ug as cd_ug,
    nome_ug as ug,
    try_strptime(data_assinatura_contrato, '%d/%m/%Y')::date as dt_assinatura,
    try_strptime(data_publica_o_dou, '%d/%m/%Y')::date as dt_publicacao_dou,
    try_strptime(data_in_cio_vig_ncia, '%d/%m/%Y')::date as dt_inicio_vigencia,
    try_strptime(data_fim_vig_ncia, '%d/%m/%Y')::date as dt_fim_vigencia,
    mascarar_dado_pessoal(c_digo_contratado, 'favorecido') as cd_contratado,
    mascarar_dado_pessoal(nome_contratado, 'favorecido') as contratado,
    try_cast(replace(valor_inicial_compra, ',', '.') as decimal(18, 2)) as valor_inicial,
    try_cast(replace(valor_final_compra, ',', '.') as decimal(18, 2)) as valor_final,
    n_mero_licita_o as numero_licitacao,
    c_digo_ug_licita_o || '-' || c_digo_modalidade_compra_licita_o || '-' || n_mero_licita_o as id_licitacao,
    c_digo_ug_licita_o as cd_ug_licitacao,
    nome_ug_licita_o as ug_licitacao,
    c_digo_modalidade_compra_licita_o as cd_modalidade_licitacao,
    modalidade_compra_licita_o as modalidade_licitacao,
    _source_file_id as id_captura

from {{ source('transparencia', 'compras') }}

)

{{ colunas_auditoria('base') }}
