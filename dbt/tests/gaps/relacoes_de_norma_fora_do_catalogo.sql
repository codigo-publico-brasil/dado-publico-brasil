{{ config(severity='warn') }}
-- Normas detalhadas (com relações) que não estão no catálogo `normas`: o ano da norma ainda não foi carregado.
select distinct r.id_norma
from {{ ref('brg_normas_relacoes') }} as r
left join {{ ref('fct_normas') }} as n on n.id_norma = r.id_norma
where n.id_norma is null
