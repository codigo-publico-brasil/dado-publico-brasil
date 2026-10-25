with source as (

    select * from {{ source('senado', 'votacoes') }}

),

renamed as (

    select
        try_cast(codigo_sessao_votacao as bigint) as id_votacao,
        try_cast(data_sessao as date) as dt_votacao,
        votacao_secreta = 'S' as fl_secreta,
        resultado_votacao as resultado,
        try_cast(total_votos_sim as integer) as votos_sim,
        try_cast(total_votos_nao as integer) as votos_nao,
        try_cast(total_votos_abstencao as integer) as votos_abstencao,
        descricao_votacao as descricao,
        informe_legislativo_sigla_colegiado as orgao_sigla,
        try_cast(codigo_materia as bigint) as id_materia,
        identificacao as materia_sigla,
        try_cast(data_apresentacao as date) as dt_materia_apresentacao,
        regexp_replace(ementa, '^\s+|\s+$', '', 'g') as materia_ementa,
        _source_file_id as id_captura

    from source

)

select * from renamed
