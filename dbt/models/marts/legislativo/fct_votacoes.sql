with proposicoes_da_votacao as (

    select
        vp.id_votacao,
        string_agg(distinct p.sigla, ', ') as proposicoes

    from {{ ref('int_votacoes_proposicoes_unidas') }} as vp

    inner join {{ ref('fct_proposicoes') }} as p
        on p.fonte = '{{ var("source_camara") }}' and p.id_proposicao = cast(vp.id_proposicao as varchar)

    group by vp.id_votacao

),

camara as (

    select
        '{{ var("source_camara") }}' as fonte,
        v.id_votacao,
        v.dt_votacao,
        v.orgao_sigla,
        v.descricao,
        v.aprovada,
        v.votos_sim,
        v.votos_nao,
        v.votos_outros,
        x.proposicoes,
        cast(null as boolean) as fl_votacao_secreta,
        cast(c.dt_captura as date) as dt_captura

    from {{ ref('stg_camara__votacoes') }} as v

    left join proposicoes_da_votacao as x on x.id_votacao = v.id_votacao

    left join {{ ref('stg_metadata__captures') }} as c on c.id_captura = v.id_captura

),

senado as (

    select
        '{{ var("source_senado") }}' as fonte,
        cast(v.id_votacao as varchar) as id_votacao,
        v.dt_votacao,
        v.orgao_sigla,
        v.descricao,
        case v.resultado when 'A' then 1 when 'R' then 0 end as aprovada,
        v.votos_sim,
        v.votos_nao,
        v.votos_abstencao as votos_outros,
        v.materia_sigla as proposicoes,
        v.fl_secreta as fl_votacao_secreta,
        cast(c.dt_captura as date) as dt_captura

    from {{ ref('stg_senado__votacoes') }} as v

    left join {{ ref('stg_metadata__captures') }} as c on c.id_captura = v.id_captura

)

select * from camara

union all

select * from senado
