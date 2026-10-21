with source as (

    select * from {{ source('camara', 'votacoes_votos') }}

),

renamed as (

    select
        id_votacao as votacao_id,
        try_cast(deputado_id as bigint) as deputado_id,
        coalesce(voto, '') as voto,
        try_cast(data_hora_voto as timestamp) as votou_em,
        try_cast(regexp_extract(deputado_uri_partido, '(\d+)$', 1) as bigint) as partido_id,
        deputado_sigla_partido as partido_sigla,
        deputado_sigla_uf as uf_sigla,
        try_cast(deputado_id_legislatura as integer) as legislatura_id,
        proper_name(deputado_nome) as deputado_nome,
        deputado_url_foto as deputado_foto_url,
        _source_file_id as source_file_id

    from source

)

select * from renamed
