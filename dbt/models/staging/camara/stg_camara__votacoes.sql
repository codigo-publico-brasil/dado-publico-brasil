with source as (

    select * from {{ source('camara', 'votacoes') }}

),

renamed as (

    select
        id as id_votacao,
        try_cast(data as date) as dt_votacao,
        try_cast(data_hora_registro as timestamp) as dt_registro,
        try_cast(id_orgao as bigint) as id_orgao,
        sigla_orgao as orgao_sigla,
        try_cast(id_evento as bigint) as id_evento,
        try_cast(aprovacao as integer) as aprovada,
        try_cast(votos_sim as integer) as votos_sim,
        try_cast(votos_nao as integer) as votos_nao,
        try_cast(votos_outros as integer) as votos_outros,
        descricao,
        _source_file_id as id_captura

    from source

)

select * from renamed
