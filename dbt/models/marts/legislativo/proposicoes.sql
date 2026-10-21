with siglas as (

    select coalesce(list(sigla), []::varchar[]) as lista

    from {{ ref('int_siglas_em_ementas_extraidas') }}

)

select
    '{{ var("source_camara") }}' as fonte,
    cast(p.proposicao_id as varchar) as proposicao_id,
    p.sigla_tipo || ' ' || coalesce(cast(p.numero as varchar), '?') || '/'
        || coalesce(cast(p.ano as varchar), '?') as sigla,
    coalesce(standardize_summary(p.ementa, s.lista), p.ementa) as ementa,
    p.ementa as ementa_oficial,
    cast(p.apresentada_em as date) as apresentada_em,
    p.situacao,
    p.ultimo_status_orgao_sigla as orgao_ultimo_status,
    cast(p.ultimo_status_em as date) as ultimo_status_em,
    '{{ var("url_proposicao_camara") }}' || cast(p.proposicao_id as varchar) as fonte_url,
    cast(c.capturado_em as date) as capturado_em

from {{ ref('stg_camara__proposicoes') }} as p

cross join siglas as s

left join {{ ref('stg_metadata__captures') }} as c on c.source_file_id = p.source_file_id
