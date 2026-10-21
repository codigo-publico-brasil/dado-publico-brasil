-- Erro se algum andamento se perdeu entre o staging e os marts.
select 1
where (select count(*) from {{ ref('stg_camara__tramitacoes') }}) <> (select count(*) from {{ ref('tramitacoes') }})
