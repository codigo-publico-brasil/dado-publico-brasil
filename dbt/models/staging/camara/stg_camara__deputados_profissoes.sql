with source as (

    select * from {{ source('camara', 'deputados_profissoes') }}

),

renamed as (

    select
        try_cast(id as bigint) as deputado_id,
        try_cast(cod_tipo_profissao as integer) as tipo_codigo,
        sentence_case(titulo) as titulo,
        try_cast(data_hora as timestamp) as registrada_em,
        _source_file_id as source_file_id

    from source

)

select * from renamed
