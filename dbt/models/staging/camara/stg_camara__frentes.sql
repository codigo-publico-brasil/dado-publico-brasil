with source as (

    select * from {{ source('camara', 'frentes') }}

),

renamed as (

    select
        try_cast(id as bigint) as frente_id,
        titulo,
        try_cast(data_criacao as date) as criada_em,
        try_cast(id_legislatura as integer) as legislatura_id,
        sentence_case(situacao) as situacao,
        try_cast(coordenador_id as bigint) as coordenador_deputado_id,
        _source_file_id as source_file_id

    from source

)

select * from renamed
