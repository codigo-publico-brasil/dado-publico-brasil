select
    '{{ var("source_camara") }}' as fonte,
    frente_id,
    id_pessoa,
    titulo,
    legislatura_id,
    inicio,
    fim

from {{ ref('int_frentes_membros_ligados_a_pessoas') }}
