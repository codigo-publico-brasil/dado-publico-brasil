{{ config(severity='warn') }}
-- Autorias de proposições de anos ainda não carregados.
select a.id_proposicao
from {{ ref('brg_proposicoes_autorias') }} as a
where not exists (
    select 1 from {{ ref('fct_proposicoes') }} as p where p.fonte = a.fonte and p.id_proposicao = a.id_proposicao
)
