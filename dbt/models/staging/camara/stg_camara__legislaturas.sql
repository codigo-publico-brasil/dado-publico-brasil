with source as (

    select * from {{ source('camara', 'legislaturas') }}

),

renamed as (

    select
        try_cast(id_legislatura as integer) as legislatura_id,
        try_cast(data_inicio as date) as inicio,
        try_cast(data_fim as date) as fim,
        try_cast(ano_eleicao as integer) as ano_eleicao,
        _source_file_id as source_file_id

    from source

)

select * from renamed
