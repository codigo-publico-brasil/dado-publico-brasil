select
    id_pessoa,
    dt_criacao

from {{ source('identity', 'pessoas') }}
