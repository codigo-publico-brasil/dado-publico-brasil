with source as (

    select * from {{ source('camara', 'deputados_ocupacoes') }}

),

renamed as (

    select
        try_cast(id as bigint) as deputado_id,
        sentence_case(titulo) as titulo,
        sentence_case(entidade) as entidade,
        entidade_uf,
        entidade_pais,
        try_cast(ano_inicio as integer) as ano_inicio,
        try_cast(ano_fim as integer) as ano_fim,
        _source_file_id as source_file_id

    from source

)

select * from renamed
