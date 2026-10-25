with source as (

    select * from {{ source('camara', 'frentes_deputados') }}

),

renamed as (

    select
        try_cast(id as bigint) as id_frente,
        try_cast(deputado_id as bigint) as id_deputado,
        try_cast(deputado_id_legislatura as integer) as id_legislatura,
        deputado_titulo as titulo,
        deputado_url_foto as deputado_foto_url,
        try_cast(data_inicio as date) as dt_inicio,
        try_cast(data_fim as date) as dt_fim,
        _source_file_id as id_captura

    from source

)

select * from renamed
