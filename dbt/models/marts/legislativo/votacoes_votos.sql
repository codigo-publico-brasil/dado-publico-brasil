select
    fonte,
    id_pessoa,
    id_votacao,
    voto,
    dt_voto,
    partido_sigla as partido,
    uf_sigla as uf

from {{ ref('int_votacoes_votos_ligados') }}
