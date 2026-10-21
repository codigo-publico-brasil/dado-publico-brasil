with source as (

    select * from {{ source('camara', 'votacoes_objetos') }}

),

renamed as (

    select
        id_votacao as votacao_id,
        try_cast(proposicao_id as bigint) as proposicao_id,
        _source_file_id as source_file_id

    from source

)

select * from renamed
