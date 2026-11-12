select
    id_verificacao,
    dt_verificacao,
    fonte,
    dataset,
    particao,
    verificacao,
    resultado,
    detalhe

from {{ source('metadata', 'fontes_verificacoes') }}
