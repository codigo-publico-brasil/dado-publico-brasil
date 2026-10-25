{{ config(severity='warn') }}
-- Candidaturas de quem já é pessoa do projeto, de eleições cujos votos já foram carregados, sem nenhum voto: a fonte
-- não os traz (por exemplo, candidatura indeferida ou renunciada). Suplente de senador e vice não têm voto próprio (o
-- voto é do titular) e ficam de fora.
select c.id_candidatura
from {{ ref('candidaturas') }} as c
where c.ano_eleicao in (select distinct ano_eleicao from {{ ref('stg_tse__votacao') }})
    and c.cargo not like '%suplente%'
    and c.cargo not like 'Vice-%'
    and not exists (select 1 from {{ ref('candidaturas_votos') }} as v where v.id_candidatura = c.id_candidatura)
