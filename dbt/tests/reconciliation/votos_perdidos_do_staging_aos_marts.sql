-- Erro se algum voto se perdeu entre o staging e os marts.
select 1
where (select count(*) from {{ ref('stg_camara__votos') }}) <> (select count(*) from {{ ref('votos') }})
