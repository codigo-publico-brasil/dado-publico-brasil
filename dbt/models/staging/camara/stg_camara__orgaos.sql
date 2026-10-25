with source as (

    select * from {{ source('camara', 'orgaos') }}

),

renamed as (

    select
        try_cast(regexp_extract(uri, '(\d+)$', 1) as bigint) as id_orgao,
        sigla,
        apelido,
        nome,
        try_cast(cod_tipo_orgao as integer) as id_tipo_orgao,
        tipo_orgao,
        cast(try_cast(data_inicio as timestamp) as date) as dt_inicio,
        cast(try_cast(data_instalacao as timestamp) as date) as dt_instalacao,
        cast(try_cast(data_fim as timestamp) as date) as dt_fim,
        sentence_case(descricao_situacao) as situacao,
        casa,
        uri as fonte_url,
        _source_file_id as id_captura

    from source

)

select * from renamed
