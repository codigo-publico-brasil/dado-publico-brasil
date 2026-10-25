select
    '{{ var("source_camara") }}' as fonte,
    id_orgao,
    sigla,
    apelido,
    nome,
    tipo_orgao as tipo,
    dt_inicio,
    dt_instalacao,
    dt_fim,
    situacao,
    casa,
    fonte_url

from {{ ref('stg_camara__orgaos') }}
