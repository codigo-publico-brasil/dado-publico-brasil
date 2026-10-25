{{ config(severity='warn') }}
-- Ligações votação-proposição de proposições de anos ainda não carregados.
select vp.id_votacao, vp.id_proposicao
from {{ ref('int_votacoes_proposicoes_unidas') }} as vp
where not exists (
    select 1 from {{ ref('proposicoes') }} as p
    where p.fonte = '{{ var("source_camara") }}' and p.id_proposicao = cast(vp.id_proposicao as varchar)
)
