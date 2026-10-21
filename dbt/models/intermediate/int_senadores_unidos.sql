-- Todo senador que o Senado informa: o cadastro mais quem só aparece nos votos (com o nome do voto mais recente).
with nos_votos as (

    select
        v.senador_id,
        arg_max(v.nome, d.data) as nome

    from {{ ref('stg_senado__votos') }} as v

    inner join {{ ref('stg_senado__votacoes') }} as d on d.votacao_id = v.votacao_id

    group by v.senador_id

)

select
    coalesce(c.senador_id, n.senador_id) as senador_id,
    coalesce(c.nome, n.nome) as nome,
    c.nome_civil,
    c.sexo

from {{ ref('stg_senado__senadores') }} as c

full outer join nos_votos as n on n.senador_id = c.senador_id
