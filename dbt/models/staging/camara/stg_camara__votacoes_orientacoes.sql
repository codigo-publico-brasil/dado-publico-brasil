with source as (

    select * from {{ source('camara', 'votacoes_orientacoes') }}

),

renamed as (

    select
        id_votacao as votacao_id,
        sigla_bancada as bancada_sigla,
        orientacao,
        _source_file_id as source_file_id

    from source

)

select * from renamed
