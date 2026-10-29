-- Erro se algum órgão se perdeu entre o staging e os marts.
select 1
where (select count(*) from {{ ref('stg_camara__orgaos') }}) <> (select count(*) from {{ ref('dim_orgaos') }})
