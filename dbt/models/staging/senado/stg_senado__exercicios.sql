-- Exercício oficial de cada senador em cada mandato (titular ou suplente), com a causa de afastamento.
-- O mesmo exercício vem no arquivo de cada legislatura que o toca: fica uma linha por senador, mandato e exercício.
with exercicios as (

    select
        try_cast(s.identificacao_parlamentar_codigo_parlamentar as bigint) as id_senador,
        m.codigo_mandato as id_mandato,
        e.codigo_exercicio as id_exercicio,
        m.descricao_participacao as participacao,
        m.uf_parlamentar as uf,
        try_cast(m.primeira_legislatura_do_mandato__data_inicio as date) as dt_mandato_inicio,
        try_cast(m.segunda_legislatura_do_mandato__data_fim as date) as mandato_fim_segunda,
        try_cast(m.primeira_legislatura_do_mandato__data_fim as date) as mandato_fim_primeira,
        try_cast(e.data_inicio as date) as dt_inicio,
        try_cast(e.data_fim as date) as dt_fim,
        e.sigla_causa_afastamento as causa_afastamento_sigla,
        e.descricao_causa_afastamento as causa_afastamento,
        s._source_file_id as id_captura

    from {{ source('senado', 'senadores') }} as s

    inner join {{ source('senado', 'senadores__mandatos_mandato') }} as m on m._dlt_parent_id = s._dlt_id

    inner join {{ source('senado', 'senadores__mandatos_mandato__exercicios__exercicio') }} as e
        on e._dlt_parent_id = m._dlt_id

)

select
    id_senador,
    id_mandato,
    id_exercicio,
    arg_max(participacao, id_captura) as participacao,
    arg_max(uf, id_captura) as uf,
    arg_max(dt_mandato_inicio, id_captura) as dt_mandato_inicio,
    arg_max(coalesce(mandato_fim_segunda, mandato_fim_primeira), id_captura) as dt_mandato_fim,
    arg_max(dt_inicio, id_captura) as dt_inicio,
    arg_max(dt_fim, id_captura) as dt_fim,
    arg_max(causa_afastamento_sigla, id_captura) as causa_afastamento_sigla,
    arg_max(causa_afastamento, id_captura) as causa_afastamento,
    max(id_captura) as id_captura

from exercicios

group by id_senador, id_mandato, id_exercicio
