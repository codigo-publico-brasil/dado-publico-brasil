select
    '{{ var("source_camara") }}' as fonte,
    id_frente,
    id_pessoa,
    titulo,
    id_legislatura,
    dt_inicio,
    dt_fim,
    id_captura,
    cast(dt_captura as date) as dt_captura

from {{ ref('int_frentes_membros_ligados') }}
