with source as (

    select * from {{ source('camara', 'deputados') }}

),

renamed as (

    select
        try_cast(regexp_extract(uri, '(\d+)$', 1) as bigint) as id_deputado,
        proper_name(nome) as nome,
        proper_name(nome_civil) as nome_civil,
        sigla_sexo as sexo,
        try_cast(data_nascimento as date) as dt_nascimento,
        try_cast(data_falecimento as date) as dt_falecimento,
        uf_nascimento,
        proper_name(municipio_nascimento) as municipio_nascimento,
        url_rede_social as rede_social_url,
        url_website as site_url,
        try_cast(id_legislatura_inicial as integer) as id_primeira_legislatura,
        try_cast(id_legislatura_final as integer) as id_ultima_legislatura,
        _source_file_id as id_captura

    from source

)

select * from renamed
