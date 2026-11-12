-- Termos aditivos dos contratos do governo federal, uma linha por termo como a fonte publica.
select
    'transparencia' as fonte,
    a.id_contrato,
    a.numero_termo_aditivo as numero,
    a.dt_publicacao,
    a.objeto,
    a.id_captura,
    cast(k.dt_captura as date) as dt_captura

from {{ ref('stg_transparencia__compras_termos_aditivos') }} as a

left join {{ ref('stg_metadata__capturas') }} as k on k.id_captura = a.id_captura
