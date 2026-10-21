{{ config(severity='warn') }}
-- Ligações votação-proposição de proposições de anos ainda não carregados.
select vp.votacao_id, vp.proposicao_id
from {{ ref('int_votacoes_proposicoes_unidas') }} as vp
where not exists (
    select 1 from {{ ref('proposicoes') }} as p
    where p.fonte = '{{ var("source_camara") }}' and p.proposicao_id = cast(vp.proposicao_id as varchar)
)
