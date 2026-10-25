with source as (

    select * from {{ source('camara', 'votacoes_orientacoes') }}

),

renamed as (

    select
        id_votacao as id_votacao,
        sigla_bancada as bancada_sigla,
        orientacao,
        _source_file_id as id_captura

    from source

)

select * from renamed
