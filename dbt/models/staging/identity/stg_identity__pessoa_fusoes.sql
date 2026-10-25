select
    id_pessoa_absorvida,
    id_pessoa_sobrevivente,
    metodo,
    try_cast(fundida_em as timestamp) as dt_fusao

from {{ source('identity', 'pessoa_fusao') }}
