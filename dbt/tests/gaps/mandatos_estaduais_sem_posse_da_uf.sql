{{ config(severity='warn') }}
-- Mandatos de deputado estadual e distrital sem data de início porque a UF não tem posse conferida em dim_cargos_posse_uf
-- (a regra vem da constituição estadual; sem fonte lida, nada é estimado). Uma linha por UF e ano de eleição.
select m.id_territorio, t.sigla, m.ano_inicio - 1 as ano_eleicao, count(*) as qtd_mandatos
from {{ ref('fct_mandatos') }} as m
left join {{ ref('dim_territorios') }} as t on t.id_territorio = m.id_territorio
where m.id_cargo in ('deputado_estadual', 'deputado_distrital') and m.dt_inicio is null
group by all
