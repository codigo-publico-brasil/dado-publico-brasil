{{ config(severity='warn') }}
-- Candidaturas de quem já é pessoa do projeto, de eleições cujos votos já foram carregados, sem nenhum voto: a fonte
-- não os traz (por exemplo, candidatura indeferida ou renunciada). Suplente de senador não tem voto próprio (o voto é
-- do titular) e fica de fora.
select c.candidatura_id
from {{ ref('candidaturas') }} as c
where c.ano_eleicao in (select distinct ano_eleicao from {{ ref('stg_tse__votacao') }})
    and c.cargo not like '%suplente%'
    and not exists (select 1 from {{ ref('votos_de_candidatos') }} as v where v.candidatura_id = c.candidatura_id)
