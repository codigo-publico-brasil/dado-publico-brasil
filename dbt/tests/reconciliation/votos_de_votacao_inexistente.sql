-- Todo voto pertence a uma votação do mesmo fonte.
select x.fonte, x.votacao_id
from {{ ref('votos') }} as x
where not exists (
    select 1 from {{ ref('votacoes') }} as v where v.fonte = x.fonte and v.votacao_id = x.votacao_id
)
