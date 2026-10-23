-- Erro se algum bem de candidato ligado a uma pessoa se perdeu entre o staging e os marts.
select 1
where (
    select count(distinct b.candidatura_id || ':' || b.ordem)
    from {{ ref('stg_tse__bens') }} as b
    inner join {{ ref('stg_identity__pessoa_identificadores') }} as i
        on i.fonte = '{{ var("source_tse") }}' and i.id_na_fonte = b.candidatura_id
) <> (select count(*) from {{ ref('bens_de_candidatos') }})
