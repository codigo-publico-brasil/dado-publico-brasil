-- Re-granularidade: uma foto por deputado, a da legislatura mais recente nos arquivos de frentes.
-- Complementa a foto dos arquivos de votos, que só existe para quem votou.
select
    deputado_id,
    arg_max(deputado_foto_url, legislatura_id) as foto_url

from {{ ref('stg_camara__frentes_membros') }}

where deputado_foto_url is not null

group by deputado_id
