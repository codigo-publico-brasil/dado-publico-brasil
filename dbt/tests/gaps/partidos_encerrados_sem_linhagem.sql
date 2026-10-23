{{ config(severity='warn') }}
-- Siglas que deixaram de aparecer nos votos (último voto há mais de um ano) e não têm evento conferido em
-- eventos_de_partidos: mudança de nome, fusão ou incorporação ainda por conferir no TSE, ou extinção.
select v.partido
from {{ ref('votos') }} as v
where v.partido is not null
    and v.partido not in ('S/Partido', 'Sem registro', 'S.PART.')
group by v.partido
having max(v.votou_em) < (select max(votou_em) from {{ ref('votos') }}) - interval 1 year
    and v.partido not in (select sigla_anterior from {{ ref('eventos_de_partidos') }})
