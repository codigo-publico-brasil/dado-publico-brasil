select
    '{{ var("source_camara") }}' as fonte,
    id_legislatura,
    dt_inicio,
    dt_fim,
    ano_eleicao

from {{ ref('stg_camara__legislaturas') }}
