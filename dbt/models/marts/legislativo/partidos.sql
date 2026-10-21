select
    '{{ var("source_camara") }}' as fonte,
    partido_id,
    sigla,
    nome

from {{ ref('stg_camara__partidos') }}
