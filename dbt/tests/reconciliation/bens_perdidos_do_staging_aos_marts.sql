-- Erro se algum bem de candidato ligado a uma pessoa se perdeu entre o staging e os marts.
select 1
where (
    select count(distinct b.id_candidatura || ':' || b.ordem)
    from {{ ref('stg_tse__bens') }} as b
    inner join {{ ref('stg_identity__pessoa_identificadores') }} as i
        on i.fonte = '{{ var("source_tse") }}' and i.id_na_fonte = b.id_candidatura
) <> (select count(*) from {{ ref('candidaturas_bens') }})
