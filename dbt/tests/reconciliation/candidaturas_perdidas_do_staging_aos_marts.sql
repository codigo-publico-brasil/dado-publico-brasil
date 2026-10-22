-- Erro se alguma candidatura ligada a uma pessoa se perdeu entre a identidade e os marts.
select 1
where (
    select count(*) from {{ ref('stg_identity__pessoa_identificadores') }} where fonte = '{{ var("source_tse") }}'
) <> (select count(*) from {{ ref('candidaturas') }})
