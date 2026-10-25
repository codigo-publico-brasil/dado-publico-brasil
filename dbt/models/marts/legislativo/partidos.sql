select
    '{{ var("source_camara") }}' as fonte,
    id_partido,
    sigla,
    sigla_original,
    nome

from {{ ref('stg_camara__partidos') }}
