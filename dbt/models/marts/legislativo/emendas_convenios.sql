-- Convênios firmados com recursos de emendas parlamentares: convenente, objeto e valor. Uma linha por convênio e emenda.
select
    'transparencia' as fonte,
    c.cd_emenda,
    c.funcao,
    c.subfuncao,
    c.localidade,
    c.tipo,
    c.dt_publicacao,
    c.convenente,
    c.objeto,
    c.convenio_numero,
    c.valor,
    cast(k.dt_captura as date) as dt_captura

from {{ ref('stg_transparencia__emendas_convenios') }} as c

left join {{ ref('stg_metadata__captures') }} as k on k.id_captura = c.id_captura
