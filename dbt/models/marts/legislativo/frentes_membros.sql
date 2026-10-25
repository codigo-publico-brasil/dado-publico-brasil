select
    '{{ var("source_camara") }}' as fonte,
    id_frente,
    id_pessoa,
    titulo,
    id_legislatura,
    dt_inicio,
    dt_fim

from {{ ref('int_frentes_membros_ligados') }}
