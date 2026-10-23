-- Exercício oficial de cada senador em cada mandato (titular ou suplente), com a causa de afastamento.
-- O mesmo exercício vem no arquivo de cada legislatura que o toca: fica uma linha por senador, mandato e exercício.
with exercicios as (

    select
        try_cast(s.identificacao_parlamentar_codigo_parlamentar as bigint) as senador_id,
        m.codigo_mandato as mandato_id,
        e.codigo_exercicio as exercicio_id,
        m.descricao_participacao as participacao,
        m.uf_parlamentar as uf,
        try_cast(m.primeira_legislatura_do_mandato__data_inicio as date) as mandato_inicio,
        try_cast(m.segunda_legislatura_do_mandato__data_fim as date) as mandato_fim_segunda,
        try_cast(m.primeira_legislatura_do_mandato__data_fim as date) as mandato_fim_primeira,
        try_cast(e.data_inicio as date) as inicio,
        try_cast(e.data_fim as date) as fim,
        e.sigla_causa_afastamento as causa_afastamento_sigla,
        e.descricao_causa_afastamento as causa_afastamento,
        s._source_file_id as source_file_id

    from {{ source('senado', 'senadores') }} as s

    inner join {{ source('senado', 'senadores__mandatos_mandato') }} as m on m._dlt_parent_id = s._dlt_id

    inner join {{ source('senado', 'senadores__mandatos_mandato__exercicios__exercicio') }} as e
        on e._dlt_parent_id = m._dlt_id

)

select
    senador_id,
    mandato_id,
    exercicio_id,
    arg_max(participacao, source_file_id) as participacao,
    arg_max(uf, source_file_id) as uf,
    arg_max(mandato_inicio, source_file_id) as mandato_inicio,
    arg_max(coalesce(mandato_fim_segunda, mandato_fim_primeira), source_file_id) as mandato_fim,
    arg_max(inicio, source_file_id) as inicio,
    arg_max(fim, source_file_id) as fim,
    arg_max(causa_afastamento_sigla, source_file_id) as causa_afastamento_sigla,
    arg_max(causa_afastamento, source_file_id) as causa_afastamento,
    max(source_file_id) as source_file_id

from exercicios

group by senador_id, mandato_id, exercicio_id
