-- Itens dos contratos do governo federal, uma linha por item como a fonte publica (a fonte pode repetir linhas idênticas).
select
    'transparencia' as fonte,
    i.id_contrato,
    i.cd_item,
    i.item,
    i.item_descricao as descricao,
    i.quantidade,
    i.valor,
    i.id_captura,
    cast(k.dt_captura as date) as dt_captura

from {{ ref('stg_transparencia__compras_itens') }} as i

left join {{ ref('stg_metadata__capturas') }} as k on k.id_captura = i.id_captura
