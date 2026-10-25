with source as (

    select * from {{ source('camara', 'partidos') }}

),

renamed as (

    select
        try_cast(id as bigint) as id_partido,
        regexp_replace(sigla, '\*+$', '') as sigla,
        sigla as sigla_original,
        proper_name(nome) as nome,
        _source_file_id as id_captura

    from source

)

select * from renamed
