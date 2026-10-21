{{ config(severity='warn') }}
-- Quem aparece só nos votos não tem cadastro.
select id_pessoa from {{ ref('pessoas') }}
where fonte = '{{ var("source_camara") }}' and data_nascimento is null
