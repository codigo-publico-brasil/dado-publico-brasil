with source as (

    select * from {{ source('camara', 'orgaos') }}

),

renamed as (

    select
        try_cast(regexp_extract(uri, '(\d+)$', 1) as bigint) as orgao_id,
        sigla,
        apelido,
        nome,
        try_cast(cod_tipo_orgao as integer) as tipo_orgao_id,
        tipo_orgao,
        cast(try_cast(data_inicio as timestamp) as date) as inicio,
        cast(try_cast(data_instalacao as timestamp) as date) as instalado_em,
        cast(try_cast(data_fim as timestamp) as date) as fim,
        sentence_case(descricao_situacao) as situacao,
        casa,
        uri as fonte_url,
        _source_file_id as source_file_id

    from source

)

select * from renamed
