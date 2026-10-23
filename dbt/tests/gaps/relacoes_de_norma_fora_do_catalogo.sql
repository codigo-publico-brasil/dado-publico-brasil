{{ config(severity='warn') }}
-- Normas detalhadas (com relações) que não estão no catálogo `normas`: o ano da norma ainda não foi carregado.
select distinct r.norma_id
from {{ ref('normas_relacoes') }} as r
left join {{ ref('normas') }} as n on n.norma_id = r.norma_id
where n.norma_id is null
