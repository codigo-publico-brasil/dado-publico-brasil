{{ config(severity='warn') }}
-- A foto só existe nos arquivos de votos e de frentes.
select id_pessoa from {{ ref('pessoas') }} where foto_url is null
