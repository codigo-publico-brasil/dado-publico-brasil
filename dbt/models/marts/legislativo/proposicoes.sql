with siglas as (

    select coalesce(list(sigla), []::varchar[]) as lista

    from {{ ref('int_siglas_em_ementas_extraidas') }}

),

camara as (

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

),

senado as (

    select
        '{{ var("source_senado") }}' as fonte,
        cast(m.materia_id as varchar) as proposicao_id,
        m.sigla,
        coalesce(standardize_summary(m.ementa, s.lista), m.ementa) as ementa,
        m.ementa as ementa_oficial,
        m.apresentada_em,
        cast(null as varchar) as situacao,
        cast(null as varchar) as orgao_ultimo_status,
        cast(null as date) as ultimo_status_em,
        '{{ var("url_materia_senado") }}' || cast(m.materia_id as varchar) as fonte_url,
        cast(c.capturado_em as date) as capturado_em

    from {{ ref('int_materias_do_senado_unicas') }} as m

    cross join siglas as s

    left join {{ ref('stg_metadata__captures') }} as c on c.source_file_id = m.source_file_id

)

select * from camara

union all

select * from senado
