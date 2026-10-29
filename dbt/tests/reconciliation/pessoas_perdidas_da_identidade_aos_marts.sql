-- Erro se uma pessoa de parlamentar (Câmara ou Senado) da identidade se perdeu antes de dim_pessoas_cadastro. As pessoas só do TSE
-- (todo eleito, ADR 0031) estão em dim_pessoas, não em dim_pessoas_cadastro, que só muda na F6.
select 1
where (
    select count(distinct id_pessoa)
    from {{ ref('stg_identity__pessoa_identificadores') }}
    where fonte in ('{{ var("source_camara") }}', '{{ var("source_senado") }}')
) <> (select count(*) from {{ ref('dim_pessoas_cadastro') }})
