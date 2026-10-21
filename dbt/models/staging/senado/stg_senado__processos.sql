with source as (

    select * from {{ source('senado', 'processos') }}

)

select
    try_cast(_item as bigint) as processo_id,
    try_cast(codigo_materia as bigint) as materia_id,
    identificacao as materia_sigla,
    tramitando = 'Sim' as tramitando,
    sentence_case(situacao_atual) as situacao,
    try_cast(data_situacao_atual as date) as situacao_em,
    try_cast(data_inicio_efetivo as date) as iniciado_em,
    sigla_casa_iniciadora as casa_iniciadora,
    norma_gerada_sigla_tipo as norma_sigla_tipo,
    norma_gerada_tipo as norma_tipo,
    try_cast(norma_gerada_numero as integer) as norma_numero,
    try_cast(norma_gerada_ano_assinatura as integer) as norma_ano,
    try_cast(norma_gerada_data_assinatura as date) as norma_assinada_em,
    try_cast(norma_gerada_data_publicacao as date) as norma_publicada_em,
    norma_gerada_descricao as norma_descricao,
    norma_gerada_sigla_veiculo_publicacao as norma_veiculo,
    _source_file_id as source_file_id

from source
