select
    id_pessoa_absorvida,
    id_pessoa_sobrevivente,
    metodo,
    dt_fusao

from {{ source('identity', 'pessoas_fusoes') }}
