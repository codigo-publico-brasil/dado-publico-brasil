with source as (

    select * from {{ source('camara', 'orgaos_deputados') }}

),

renamed as (

    select
        try_cast(regexp_extract(uri_orgao, '(\d+)$', 1) as bigint) as orgao_id,
        try_cast(regexp_extract(uri_deputado, '(\d+)$', 1) as bigint) as deputado_id,
        sigla_orgao as orgao_sigla,
        cargo,
        sigla_partido as partido_sigla,
        sigla_uf as uf_sigla,
        try_cast(data_inicio as date) as inicio,
        try_cast(data_fim as date) as fim,
        _source_file_id as source_file_id

    from source

)

select * from renamed
