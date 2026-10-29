with siglas as (

    select coalesce(list(sigla), []::varchar[]) as lista

    from {{ ref('int_ementas_siglas_extraidas') }}

),

camara as (

    select
    '{{ var("source_camara") }}' as fonte,
    cast(p.id_proposicao as varchar) as id_proposicao,
    p.sigla_tipo || ' ' || coalesce(cast(p.numero as varchar), '?') || '/'
        || coalesce(cast(p.ano as varchar), '?') as sigla,
    coalesce(standardize_summary(p.ementa, s.lista), p.ementa) as ementa,
    p.ementa as ementa_oficial,
    cast(p.dt_apresentacao as date) as dt_apresentacao,
    p.situacao,
    p.ultimo_status_orgao_sigla as orgao_ultimo_status,
    cast(p.dt_ultimo_status as date) as dt_ultimo_status,
    '{{ var("url_proposicao_camara") }}' || cast(p.id_proposicao as varchar) as fonte_url,
    cast(c.dt_captura as date) as dt_captura

from {{ ref('stg_camara__proposicoes') }} as p

cross join siglas as s

left join {{ ref('stg_metadata__captures') }} as c on c.id_captura = p.id_captura

),

senado as (

    select
        '{{ var("source_senado") }}' as fonte,
        cast(m.id_materia as varchar) as id_proposicao,
        m.sigla,
        coalesce(standardize_summary(m.ementa, s.lista), m.ementa) as ementa,
        m.ementa as ementa_oficial,
        m.dt_apresentacao,
        pr.situacao,
        cast(null as varchar) as orgao_ultimo_status,
        pr.dt_situacao as dt_ultimo_status,
        '{{ var("url_materia_senado") }}' || cast(m.id_materia as varchar) as fonte_url,
        cast(c.dt_captura as date) as dt_captura

    from {{ ref('int_senado_materias_unicas') }} as m

    cross join siglas as s

    left join {{ ref('stg_senado__processos') }} as pr on pr.id_materia = m.id_materia

    left join {{ ref('stg_metadata__captures') }} as c on c.id_captura = m.id_captura

)

select * from camara

union all

select * from senado
