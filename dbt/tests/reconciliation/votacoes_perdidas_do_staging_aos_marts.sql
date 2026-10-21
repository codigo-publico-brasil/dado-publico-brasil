select 1
where (select count(*) from {{ ref('stg_camara__votacoes') }}) <> (select count(*) from {{ ref('votacoes') }})
