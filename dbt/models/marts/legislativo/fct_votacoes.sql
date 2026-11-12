-- O órgão do Senado liga pela sigla do colegiado, só quando ela identifica um colegiado do Senado em atividade (a fonte de
-- votações não traz o código; o colegiado extinto e a sigla repetida ficam sem id_orgao, e o teste de aviso mede).
with colegiados_do_senado as (

    select sigla, min(id_orgao) as id_orgao

    from {{ ref('dim_orgaos') }}

    where fonte = '{{ var("source_senado") }}' and casa = 'Senado Federal'

    group by sigla

    having count(*) = 1

),

proposicoes_da_votacao as (

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
        case when v.id_orgao is not null then '{{ var("source_camara") }}-' || v.id_orgao end as id_orgao,
        v.orgao_sigla,
        v.descricao,
        v.aprovada,
        v.votos_sim,
        v.votos_nao,
        v.votos_outros,
        x.proposicoes,
        cast(null as boolean) as fl_votacao_secreta,
        v.id_captura,
        cast(c.dt_captura as date) as dt_captura

    from {{ ref('stg_camara__votacoes') }} as v

    left join proposicoes_da_votacao as x on x.id_votacao = v.id_votacao

    left join {{ ref('stg_metadata__capturas') }} as c on c.id_captura = v.id_captura

),

senado as (

    select
        '{{ var("source_senado") }}' as fonte,
        cast(v.id_votacao as varchar) as id_votacao,
        v.dt_votacao,
        o.id_orgao,
        v.orgao_sigla,
        v.descricao,
        case v.resultado when 'A' then 1 when 'R' then 0 end as aprovada,
        v.votos_sim,
        v.votos_nao,
        v.votos_abstencao as votos_outros,
        v.materia_sigla as proposicoes,
        v.fl_secreta as fl_votacao_secreta,
        v.id_captura,
        cast(c.dt_captura as date) as dt_captura

    from {{ ref('stg_senado__votacoes') }} as v

    left join colegiados_do_senado as o on o.sigla = v.orgao_sigla

    left join {{ ref('stg_metadata__capturas') }} as c on c.id_captura = v.id_captura

)

select * from camara

union all

select * from senado
