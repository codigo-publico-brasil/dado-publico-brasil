with source as (

    select * from {{ source('camara', 'frentes_deputados') }}

),

renamed as (

    select
        try_cast(id as bigint) as frente_id,
        try_cast(deputado_id as bigint) as deputado_id,
        try_cast(deputado_id_legislatura as integer) as legislatura_id,
        deputado_titulo as titulo,
        deputado_url_foto as deputado_foto_url,
        try_cast(data_inicio as date) as inicio,
        try_cast(data_fim as date) as fim,
        _source_file_id as source_file_id

    from source

)

select * from renamed
