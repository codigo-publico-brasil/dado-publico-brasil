{{ config(severity='warn') }}
-- Quem aparece só nos votos não tem cadastro.
select id_pessoa from {{ ref('dim_pessoas_cadastro') }}
where fonte = '{{ var("source_camara") }}' and dt_nascimento is null
