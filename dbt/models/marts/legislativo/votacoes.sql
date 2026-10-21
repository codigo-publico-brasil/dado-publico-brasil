with proposicoes_da_votacao as (

    select
        vp.votacao_id,
        string_agg(distinct p.sigla, ', ') as proposicoes

    from {{ ref('int_votacoes_proposicoes_unidas') }} as vp

    inner join {{ ref('proposicoes') }} as p
        on p.fonte = '{{ var("source_camara") }}' and p.proposicao_id = cast(vp.proposicao_id as varchar)

    group by vp.votacao_id

),

camara as (

    select
        '{{ var("source_camara") }}' as fonte,
        v.votacao_id,
        v.data,
        v.orgao_sigla,
        v.descricao,
        v.aprovada,
        v.votos_sim,
        v.votos_nao,
        v.votos_outros,
        x.proposicoes,
        cast(null as boolean) as votacao_secreta,
        cast(c.capturado_em as date) as capturado_em

    from {{ ref('stg_camara__votacoes') }} as v

    left join proposicoes_da_votacao as x on x.votacao_id = v.votacao_id

    left join {{ ref('stg_metadata__captures') }} as c on c.source_file_id = v.source_file_id

),

senado as (

    select
        '{{ var("source_senado") }}' as fonte,
        cast(v.votacao_id as varchar) as votacao_id,
        v.data,
        v.orgao_sigla,
        v.descricao,
        case v.resultado when 'A' then 1 when 'R' then 0 end as aprovada,
        v.votos_sim,
        v.votos_nao,
        v.votos_abstencao as votos_outros,
        v.materia_sigla as proposicoes,
        v.secreta as votacao_secreta,
        cast(c.capturado_em as date) as capturado_em

    from {{ ref('stg_senado__votacoes') }} as v

    left join {{ ref('stg_metadata__captures') }} as c on c.source_file_id = v.source_file_id

)

select * from camara

union all

select * from senado
