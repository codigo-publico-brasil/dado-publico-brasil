-- Re-granularidade: uma linha por pessoa, com o que ela fez (votos, propostas, legislaturas).
with votacoes_votos as (

    select
        id_pessoa,
        count(*) as qtd_votos,
        arg_max(partido_sigla, dt_voto) as ultimo_partido,
        arg_max(uf_sigla, dt_voto) as ultima_uf,
        max(dt_voto) as dt_ultimo_voto,
        min(id_legislatura) as primeira_legislatura_com_voto,
        max(id_legislatura) as ultima_legislatura_com_voto

    from {{ ref('int_votacoes_votos_ligados') }}

    group by id_pessoa

),

propostas as (

    select id_pessoa, count(*) as qtd_propostas

    from {{ ref('int_proposicoes_autorias_ligadas') }}

    where id_pessoa is not null

    group by id_pessoa

)

select
    coalesce(votacoes_votos.id_pessoa, propostas.id_pessoa) as id_pessoa,
    coalesce(votacoes_votos.qtd_votos, 0) as qtd_votos,
    coalesce(propostas.qtd_propostas, 0) as qtd_propostas,
    votacoes_votos.ultimo_partido,
    votacoes_votos.ultima_uf,
    votacoes_votos.dt_ultimo_voto,
    votacoes_votos.primeira_legislatura_com_voto,
    votacoes_votos.ultima_legislatura_com_voto

from votacoes_votos

full outer join propostas on propostas.id_pessoa = votacoes_votos.id_pessoa
