select
    '{{ var("source_camara") }}' as fonte,
    id_legislatura,
    dt_inicio,
    dt_fim,
    ano_eleicao,
    id_captura,
    cast(dt_captura as date) as dt_captura

from {{ ref('stg_camara__legislaturas') }}
