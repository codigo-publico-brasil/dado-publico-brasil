-- Todo andamento pertence a uma proposição do mesmo fonte.
select t.fonte, t.id_proposicao
from {{ ref('fct_proposicoes_tramitacoes') }} as t
where not exists (
    select 1 from {{ ref('fct_proposicoes') }} as p where p.fonte = t.fonte and p.id_proposicao = t.id_proposicao
)
