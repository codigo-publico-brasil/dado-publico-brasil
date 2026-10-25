with source as (

    select * from {{ source('camara', 'proposicoes_tramitacoes') }}

),

renamed as (

    select
        try_cast(_item as bigint) as id_proposicao,
        try_cast(sequencia as integer) as sequencia,
        try_cast(data_hora as timestamp) as dt_registro,
        sigla_orgao as orgao_sigla,
        regime,
        descricao_tramitacao as descricao,
        try_cast(cod_tipo_tramitacao as integer) as id_tipo,
        sentence_case(descricao_situacao) as situacao,
        try_cast(cod_situacao as integer) as id_situacao,
        despacho,
        ambito,
        apreciacao,
        _source_file_id as id_captura

    from source

)

select * from renamed
