-- Erro se algum órgão se perdeu entre o staging e os marts (Câmara e colegiados do Senado).
select 1
where (select count(*) from {{ ref('stg_camara__orgaos') }})
    + (select count(*) from {{ ref('stg_senado__colegiados') }}) <> (select count(*) from {{ ref('dim_orgaos') }})
