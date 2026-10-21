with source as (

    select * from {{ source('camara', 'votacoes') }}

),

renamed as (

    select
        id as votacao_id,
        try_cast(data as date) as data,
        try_cast(data_hora_registro as timestamp) as registrada_em,
        try_cast(id_orgao as bigint) as orgao_id,
        sigla_orgao as orgao_sigla,
        try_cast(id_evento as bigint) as evento_id,
        try_cast(aprovacao as integer) as aprovada,
        try_cast(votos_sim as integer) as votos_sim,
        try_cast(votos_nao as integer) as votos_nao,
        try_cast(votos_outros as integer) as votos_outros,
        descricao,
        _source_file_id as source_file_id

    from source

)

select * from renamed
