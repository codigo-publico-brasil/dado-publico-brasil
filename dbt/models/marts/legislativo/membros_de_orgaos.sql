select
    '{{ var("source_camara") }}' as fonte,
    orgao_id,
    orgao_sigla,
    id_pessoa,
    cargo,
    partido_sigla as partido,
    uf_sigla as uf,
    inicio,
    fim

from {{ ref('int_orgaos_membros_ligados_a_pessoas') }}
