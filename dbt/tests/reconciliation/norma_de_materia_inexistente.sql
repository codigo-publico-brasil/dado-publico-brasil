-- Toda norma gerada pertence a uma matéria do mesmo fonte.
select n.fonte, n.proposicao_id
from {{ ref('normas_geradas') }} as n
where not exists (
    select 1 from {{ ref('proposicoes') }} as p where p.fonte = n.fonte and p.proposicao_id = n.proposicao_id
)
