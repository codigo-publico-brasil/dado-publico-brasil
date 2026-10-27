-- Erro se a soma de votos das candidaturas ligadas a pessoas muda entre o staging e os marts.
select 1
where (
    select coalesce(sum(v.votos_nominais), 0)
    from {{ ref('stg_tse__votacao') }} as v
    where v.id_candidatura in (
        select id_na_fonte from {{ ref('stg_identity__pessoa_identificadores') }} where fonte = '{{ var("source_tse") }}' and id_tipo = '{{ var("id_type_tse") }}'
    )
) <> (select coalesce(sum(votos_nominais), 0) from {{ ref('candidaturas_votos') }})
