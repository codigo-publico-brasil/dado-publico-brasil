{{ config(severity='warn') }}
-- Votações ligadas a uma proposição ou matéria que não está carregada em fct_proposicoes (anos ainda não carregados).
select vp.fonte, vp.id_votacao, vp.id_proposicao
from {{ ref('brg_votacoes_proposicoes') }} as vp
where not exists (
    select 1 from {{ ref('fct_proposicoes') }} as p where p.fonte = vp.fonte and p.id_proposicao = vp.id_proposicao
)
