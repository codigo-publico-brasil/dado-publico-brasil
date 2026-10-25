with source as (

    select * from {{ source('camara', 'deputados_profissoes') }}

),

renamed as (

    select
        try_cast(id as bigint) as id_deputado,
        try_cast(cod_tipo_profissao as integer) as cd_tipo,
        sentence_case(titulo) as titulo,
        try_cast(data_hora as timestamp) as dt_registro,
        _source_file_id as id_captura

    from source

)

select * from renamed
