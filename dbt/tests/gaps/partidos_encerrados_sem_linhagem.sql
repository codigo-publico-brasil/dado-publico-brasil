{{ config(severity='warn') }}
-- Siglas que deixaram de aparecer nos votos (último voto há mais de um ano) e não têm evento conferido em
-- eventos_de_partidos e que não concorrem mais: mudança de nome, fusão ou incorporação ainda por conferir no TSE, ou extinção.
with ativos as (

    -- siglas que ainda concorrem na última eleição carregada: o partido continua, só deixou de ter parlamentar votando (PRTB)
    select distinct upper(partido_sigla) as sigla
    from {{ ref('stg_tse__candidaturas') }}
    where ano_eleicao = (select max(ano_eleicao) from {{ ref('stg_tse__candidaturas') }})

)

select v.partido
from {{ ref('votacoes_votos') }} as v
where v.partido is not null
    and v.partido not in ('S/Partido', 'Sem registro', 'S.PART.')
group by v.partido
having max(v.dt_voto) < (select max(dt_voto) from {{ ref('votacoes_votos') }}) - interval 1 year
    and v.partido not in (select sigla_anterior from {{ ref('partidos_eventos') }})
    and upper(v.partido) not in (select sigla from ativos)
