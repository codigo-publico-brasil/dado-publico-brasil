-- Toda norma gerada pertence a uma matéria do mesmo fonte.
select n.fonte, n.id_proposicao
from {{ ref('normas_geradas') }} as n
where not exists (
    select 1 from {{ ref('proposicoes') }} as p where p.fonte = n.fonte and p.id_proposicao = n.id_proposicao
)
