-- Todo andamento pertence a uma proposição do mesmo fonte.
select t.fonte, t.proposicao_id
from {{ ref('tramitacoes') }} as t
where not exists (
    select 1 from {{ ref('proposicoes') }} as p where p.fonte = t.fonte and p.proposicao_id = t.proposicao_id
)
