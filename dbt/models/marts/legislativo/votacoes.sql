with proposicoes_da_votacao as (

    select
        vp.votacao_id,
        string_agg(distinct p.sigla, ', ') as proposicoes

    from {{ ref('int_votacoes_proposicoes_unidas') }} as vp

    inner join {{ ref('proposicoes') }} as p on p.proposicao_id = cast(vp.proposicao_id as varchar)

    group by vp.votacao_id

)

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
    cast(c.capturado_em as date) as capturado_em

from {{ ref('stg_camara__votacoes') }} as v

left join proposicoes_da_votacao as x on x.votacao_id = v.votacao_id

left join {{ ref('stg_metadata__captures') }} as c on c.source_file_id = v.source_file_id
