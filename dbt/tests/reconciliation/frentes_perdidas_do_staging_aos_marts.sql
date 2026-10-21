-- Erro se alguma frente se perdeu entre o staging e os marts.
select 1
where (select count(*) from {{ ref('stg_camara__frentes') }}) <> (select count(*) from {{ ref('frentes') }})
