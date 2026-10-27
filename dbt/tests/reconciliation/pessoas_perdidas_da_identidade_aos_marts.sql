-- Erro se uma pessoa de parlamentar (Câmara ou Senado) da identidade se perdeu antes de marts.pessoas. As pessoas só do TSE
-- (todo eleito, ADR 0031) estão em core.pessoas, não em marts.pessoas, que só muda na F6.
select 1
where (
    select count(distinct id_pessoa)
    from {{ ref('stg_identity__pessoa_identificadores') }}
    where fonte in ('{{ var("source_camara") }}', '{{ var("source_senado") }}')
) <> (select count(*) from {{ ref('pessoas') }})
