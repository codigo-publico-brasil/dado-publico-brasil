-- Erro se alguma votação se perdeu entre o staging e os marts (todas as fontes).
select 1
where (select count(*) from {{ ref('stg_camara__votacoes') }})
    + (select count(*) from {{ ref('stg_senado__votacoes') }}) <> (select count(*) from {{ ref('votacoes') }})
