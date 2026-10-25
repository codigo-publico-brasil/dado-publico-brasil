-- Todo voto pertence a uma votação do mesmo fonte.
select x.fonte, x.id_votacao
from {{ ref('votacoes_votos') }} as x
where not exists (
    select 1 from {{ ref('votacoes') }} as v where v.fonte = x.fonte and v.id_votacao = x.id_votacao
)
