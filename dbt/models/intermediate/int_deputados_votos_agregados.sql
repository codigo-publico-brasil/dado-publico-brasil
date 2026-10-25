-- Re-granularidade: de um registro por voto para um por deputado, com o nome e a foto mais
-- recentes vistos nos arquivos de votos (a foto só existe neles).
select
    id_deputado,
    arg_max(deputado_nome, dt_voto) as nome,
    arg_max(deputado_foto_url, dt_voto) filter (where deputado_foto_url is not null) as foto_url

from {{ ref('stg_camara__votos') }}

group by id_deputado
