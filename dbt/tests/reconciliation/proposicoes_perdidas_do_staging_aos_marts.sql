-- Erro se alguma proposição se perdeu entre o staging e os marts (todas as fontes).
select 1
where (select count(*) from {{ ref('stg_camara__proposicoes') }})
    + (select count(*) from {{ ref('int_senado_materias_unicas') }}) <> (select count(*) from {{ ref('proposicoes') }})
