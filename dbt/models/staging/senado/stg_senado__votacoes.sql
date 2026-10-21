with source as (

    select * from {{ source('senado', 'votacoes') }}

),

renamed as (

    select
        try_cast(codigo_sessao_votacao as bigint) as votacao_id,
        try_cast(data_sessao as date) as data,
        votacao_secreta = 'S' as secreta,
        resultado_votacao as resultado,
        try_cast(total_votos_sim as integer) as votos_sim,
        try_cast(total_votos_nao as integer) as votos_nao,
        try_cast(total_votos_abstencao as integer) as votos_abstencao,
        descricao_votacao as descricao,
        informe_legislativo_sigla_colegiado as orgao_sigla,
        try_cast(codigo_materia as bigint) as materia_id,
        identificacao as materia_sigla,
        try_cast(data_apresentacao as date) as materia_apresentada_em,
        regexp_replace(ementa, '^\s+|\s+$', '', 'g') as materia_ementa,
        _source_file_id as source_file_id

    from source

)

select * from renamed
