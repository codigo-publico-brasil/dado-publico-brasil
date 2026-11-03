select
    id_pessoa,
    fonte,
    id_tipo,
    id_na_fonte,
    metodo,
    confirmado_por,
    dt_ligacao

from {{ source('identity', 'pessoas_identificadores') }}
