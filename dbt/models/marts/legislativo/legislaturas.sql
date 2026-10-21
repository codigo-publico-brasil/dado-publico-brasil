select
    '{{ var("source_camara") }}' as fonte,
    legislatura_id,
    inicio,
    fim,
    ano_eleicao

from {{ ref('stg_camara__legislaturas') }}
