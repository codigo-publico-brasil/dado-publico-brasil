select
    '{{ var("source_camara") }}' as fonte,
    id_partido,
    sigla,
    sigla_original,
    nome,
    id_captura,
    cast(dt_captura as date) as dt_captura

from {{ ref('stg_camara__partidos') }}
