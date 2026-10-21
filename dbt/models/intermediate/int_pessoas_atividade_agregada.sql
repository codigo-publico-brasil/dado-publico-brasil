-- Re-granularidade: uma linha por pessoa, com o que ela fez (votos, propostas, legislaturas).
with votos as (

    select
        id_pessoa,
        count(*) as qtd_votos,
        arg_max(partido_sigla, votou_em) as ultimo_partido,
        arg_max(uf_sigla, votou_em) as ultima_uf,
        max(votou_em) as ultimo_voto_em,
        min(legislatura_id) as primeira_legislatura_com_voto,
        max(legislatura_id) as ultima_legislatura_com_voto

    from {{ ref('int_votos_ligados_a_pessoas') }}

    group by id_pessoa

),

propostas as (

    select id_pessoa, count(*) as qtd_propostas

    from {{ ref('int_autorias_ligadas_a_pessoas') }}

    where id_pessoa is not null

    group by id_pessoa

)

select
    coalesce(votos.id_pessoa, propostas.id_pessoa) as id_pessoa,
    coalesce(votos.qtd_votos, 0) as qtd_votos,
    coalesce(propostas.qtd_propostas, 0) as qtd_propostas,
    votos.ultimo_partido,
    votos.ultima_uf,
    votos.ultimo_voto_em,
    votos.primeira_legislatura_com_voto,
    votos.ultima_legislatura_com_voto

from votos

full outer join propostas on propostas.id_pessoa = votos.id_pessoa
