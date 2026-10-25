with source as (

    select * from {{ source('camara', 'legislaturas') }}

),

renamed as (

    select
        try_cast(id_legislatura as integer) as id_legislatura,
        try_cast(data_inicio as date) as dt_inicio,
        try_cast(data_fim as date) as dt_fim,
        try_cast(ano_eleicao as integer) as ano_eleicao,
        _source_file_id as id_captura

    from source

)

select * from renamed
