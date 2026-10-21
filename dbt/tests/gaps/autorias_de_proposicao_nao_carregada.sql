{{ config(severity='warn') }}
-- Autorias de proposições de anos ainda não carregados.
select a.proposicao_id
from {{ ref('autorias') }} as a
where not exists (select 1 from {{ ref('proposicoes') }} as p where p.proposicao_id = a.proposicao_id)
