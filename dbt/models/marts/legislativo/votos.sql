select
    '{{ var("source_camara") }}' as fonte,
    id_pessoa,
    votacao_id,
    voto,
    votou_em,
    partido_sigla as partido,
    uf_sigla as uf

from {{ ref('int_votos_ligados_a_pessoas') }}
