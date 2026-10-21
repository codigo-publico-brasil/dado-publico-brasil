-- Re-granularidade: de um registro por voto para um por deputado, com o nome e a foto mais
-- recentes vistos nos arquivos de votos (a foto só existe neles).
select
    deputado_id,
    arg_max(deputado_nome, votou_em) as nome,
    arg_max(deputado_foto_url, votou_em) filter (where deputado_foto_url is not null) as foto_url

from {{ ref('stg_camara__votos') }}

group by deputado_id
