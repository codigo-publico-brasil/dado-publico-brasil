select 1
where (select count(*) from {{ ref('stg_camara__proposicoes') }}) <> (select count(*) from {{ ref('proposicoes') }})
