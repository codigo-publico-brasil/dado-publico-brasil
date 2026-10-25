with source as (

    select * from {{ source('camara', 'proposicoes') }}

),

renamed as (

    select
        try_cast(id as bigint) as id_proposicao,
        sigla_tipo,
        try_cast(numero as integer) as numero,
        try_cast(ano as integer) as ano,
        descricao_tipo,
        ementa,
        try_cast(data_apresentacao as timestamp) as dt_apresentacao,
        url_inteiro_teor,
        sentence_case(ultimo_status_descricao_situacao) as situacao,
        try_cast(ultimo_status_data_hora as timestamp) as dt_ultimo_status,
        ultimo_status_sigla_orgao as ultimo_status_orgao_sigla,
        ultimo_status_descricao_tramitacao as tramitacao,
        ultimo_status_regime as regime,
        ultimo_status_apreciacao as apreciacao,
        _source_file_id as id_captura

    from source

)

select * from renamed
