-- Erro se algum exercício do Senado se perdeu entre o staging e os marts (todo senador tem pessoa).
select 1
where (select count(*) from {{ ref('stg_senado__exercicios') }}) <> (select count(*) from {{ ref('exercicios') }})
