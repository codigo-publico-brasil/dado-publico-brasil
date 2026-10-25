with source as (

    select * from {{ source('camara', 'frentes') }}

),

renamed as (

    select
        try_cast(id as bigint) as id_frente,
        titulo,
        try_cast(data_criacao as date) as dt_criacao,
        try_cast(id_legislatura as integer) as id_legislatura,
        sentence_case(situacao) as situacao,
        try_cast(coordenador_id as bigint) as id_coordenador_deputado,
        _source_file_id as id_captura

    from source

)

select * from renamed
