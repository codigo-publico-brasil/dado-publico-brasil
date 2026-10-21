{{ config(severity='warn') }}
-- A foto só existe nos arquivos de votos e de frentes.
select id_pessoa from {{ ref('pessoas') }} where fonte = '{{ var("source_camara") }}' and foto_url is null
