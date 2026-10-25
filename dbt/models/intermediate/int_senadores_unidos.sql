-- Todo senador que o Senado informa: o cadastro mais quem só aparece nos votos (com o nome do voto mais recente).
with nos_votos as (

    select
        v.id_senador,
        arg_max(v.nome, d.dt_votacao) as nome

    from {{ ref('stg_senado__votos') }} as v

    inner join {{ ref('stg_senado__votacoes') }} as d on d.id_votacao = v.id_votacao

    group by v.id_senador

)

select
    coalesce(c.id_senador, n.id_senador) as id_senador,
    coalesce(c.nome, n.nome) as nome,
    c.nome_civil,
    c.sexo

from {{ ref('stg_senado__senadores') }} as c

full outer join nos_votos as n on n.id_senador = c.id_senador
