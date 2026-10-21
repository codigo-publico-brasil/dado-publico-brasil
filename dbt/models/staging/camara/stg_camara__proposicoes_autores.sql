with source as (

    select * from {{ source('camara', 'proposicoes_autores') }}

),

renamed as (

    select
        try_cast(id_proposicao as bigint) as proposicao_id,
        coalesce(try_cast(ordem_assinatura as integer), 0) as ordem_assinatura,
        proper_name(nome_autor) as nome_autor,
        try_cast(id_deputado_autor as bigint) as deputado_id,
        try_cast(cod_tipo_autor as integer) as tipo_autor_codigo,
        sentence_case(tipo_autor) as tipo_autor,
        sigla_partido_autor as partido_sigla,
        sigla_uf_autor as uf_sigla,
        try_cast(proponente as integer) as proponente,
        uri_autor as autor_uri,
        _source_file_id as source_file_id

    from source

)

select * from renamed
