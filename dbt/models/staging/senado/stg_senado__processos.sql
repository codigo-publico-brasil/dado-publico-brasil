with source as (

    select * from {{ source('senado', 'processos') }}

)

select
    try_cast(_item as bigint) as id_processo,
    try_cast(codigo_materia as bigint) as id_materia,
    identificacao as materia_sigla,
    tramitando = 'Sim' as fl_tramitando,
    sentence_case(situacao_atual) as situacao,
    try_cast(data_situacao_atual as date) as dt_situacao,
    try_cast(data_inicio_efetivo as date) as dt_inicio,
    sigla_casa_iniciadora as casa_iniciadora,
    try_cast(norma_gerada_codigo as bigint) as id_norma,
    norma_gerada_sigla_tipo as norma_sigla_tipo,
    norma_gerada_tipo as norma_tipo,
    try_cast(norma_gerada_numero as integer) as norma_numero,
    try_cast(norma_gerada_ano_assinatura as integer) as norma_ano,
    try_cast(norma_gerada_data_assinatura as date) as dt_norma_assinatura,
    try_cast(norma_gerada_data_publicacao as date) as dt_norma_publicacao,
    norma_gerada_descricao as norma_descricao,
    norma_gerada_sigla_veiculo_publicacao as norma_veiculo,
    _source_file_id as id_captura

from source
