select
    '{{ var("source_camara") }}' as fonte,
    id_orgao,
    orgao_sigla,
    id_pessoa,
    cargo,
    partido_sigla as partido,
    uf_sigla as uf,
    dt_inicio,
    dt_fim

from {{ ref('int_orgaos_membros_ligados') }}
