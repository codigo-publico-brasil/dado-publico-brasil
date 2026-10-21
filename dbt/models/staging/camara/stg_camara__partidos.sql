with source as (

    select * from {{ source('camara', 'partidos') }}

),

renamed as (

    select
        try_cast(id as bigint) as partido_id,
        sigla,
        proper_name(nome) as nome,
        _source_file_id as source_file_id

    from source

)

select * from renamed
