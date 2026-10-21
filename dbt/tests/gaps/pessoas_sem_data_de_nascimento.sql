{{ config(severity='warn') }}
-- Quem aparece só nos votos não tem cadastro.
select id_pessoa from {{ ref('pessoas') }} where data_nascimento is null
