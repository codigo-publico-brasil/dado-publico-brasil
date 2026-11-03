-- Cada período em que uma pessoa ocupa um cargo num território: a camada semântica da ocupação (ADR de ocupação de cargo).
-- Uma linha por período. O exercício que a Câmara e o Senado publicam vence (fim real quando há, suplente que assumiu,
-- eleito em eleição suplementar); o mandato da eleição cobre o resto, com o fim previsto pela duração do cargo (cassação e
-- renúncia desses cargos não aparecem, issue 162). A precedência é por `id_candidatura`: o mandato que um exercício cumpre
-- não gera outra linha. Sem data de posse (por exemplo, deputado estadual de 2026), o mandato entra com `dt_inicio` vazio
-- e `ano_inicio` preenchido.
-- Partido, por ordem: o da candidatura que o exercício cumpre (TSE), o do exercício (informado pelo histórico da Câmara ou
-- derivado do último registro). `base_partido` diz qual.
with exercicios as (

    select
        'exercicio' as base_ocupacao,
        e.fonte,
        'exercicio:' || e.id_exercicio as id_ocupacao,
        e.id_pessoa,
        e.id_cargo,
        e.id_territorio,
        coalesce(m.id_partido, e.id_partido) as id_partido,
        if(m.id_partido is not null, 'informado', e.base_partido) as base_partido,
        e.id_candidatura,
        e.id_exercicio,
        cast(year(e.dt_inicio) as integer) as ano_inicio,
        e.dt_inicio,
        'informado' as base_dt_inicio,
        coalesce(e.dt_fim, e.dt_mandato_fim) as dt_fim,
        if(e.dt_fim is not null, 'informado', 'previsto') as base_dt_fim,
        e.id_captura,
        e.dt_captura

    from {{ ref('fct_exercicios') }} as e

    left join {{ ref('fct_mandatos') }} as m on m.id_candidatura = e.id_candidatura

    where e.id_pessoa is not null and e.dt_inicio is not null

),

mandatos as (

    select
        'mandato' as base_ocupacao,
        m.fonte,
        'mandato:' || m.id_candidatura as id_ocupacao,
        m.id_pessoa,
        m.id_cargo,
        m.id_territorio,
        m.id_partido,
        if(m.id_partido is not null, 'informado', null) as base_partido,
        m.id_candidatura,
        cast(null as varchar) as id_exercicio,
        m.ano_inicio,
        m.dt_inicio,
        m.base_dt_inicio,
        m.dt_fim_prevista as dt_fim,
        if(m.dt_fim_prevista is not null, 'previsto', null) as base_dt_fim,
        m.id_captura,
        m.dt_captura

    from {{ ref('fct_mandatos') }} as m

    where m.id_pessoa is not null
        and not exists (select 1 from {{ ref('fct_exercicios') }} as e where e.id_candidatura = m.id_candidatura)

)

select * from exercicios

union all

select * from mandatos
