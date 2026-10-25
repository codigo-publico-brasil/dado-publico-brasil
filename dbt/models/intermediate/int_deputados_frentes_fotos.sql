-- Re-granularidade: uma foto por deputado, a da legislatura mais recente nos arquivos de frentes.
-- Complementa a foto dos arquivos de votos, que só existe para quem votou.
select
    id_deputado,
    arg_max(deputado_foto_url, id_legislatura) as foto_url

from {{ ref('stg_camara__frentes_membros') }}

where deputado_foto_url is not null

group by id_deputado
