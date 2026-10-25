-- Erro se algum voto se perdeu entre o staging e os marts (todas as fontes).
select 1
where (select count(*) from {{ ref('stg_camara__votos') }})
    + (select count(*) from {{ ref('stg_senado__votos') }}) <> (select count(*) from {{ ref('votacoes_votos') }})
