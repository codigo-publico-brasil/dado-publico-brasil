with source as (

    select * from {{ source('camara', 'deputados_historico') }}

),

renamed as (

    select
        try_cast(regexp_extract(_item, '(\d+)$', 1) as bigint) as id_deputado,
        try_cast(id_legislatura as integer) as id_legislatura,
        try_cast(data_hora as timestamp) as dt_registro,
        situacao,
        condicao_eleitoral,
        descricao_status as descricao,
        proper_name(nome) as nome,
        proper_name(nome_eleitoral) as nome_eleitoral,
        sigla_partido as partido_sigla,
        sigla_uf as uf_sigla,
        _source_file_id as id_captura

    from source

)

select * from renamed
