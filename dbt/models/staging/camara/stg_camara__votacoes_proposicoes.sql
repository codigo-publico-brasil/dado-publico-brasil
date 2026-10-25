with source as (

    select * from {{ source('camara', 'votacoes_proposicoes') }}

),

renamed as (

    select
        id_votacao as id_votacao,
        try_cast(proposicao_id as bigint) as id_proposicao,
        _source_file_id as id_captura

    from source

)

select * from renamed
