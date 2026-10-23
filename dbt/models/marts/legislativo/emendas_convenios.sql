-- Convênios firmados com recursos de emendas parlamentares: convenente, objeto e valor. Uma linha por convênio e emenda.
select
    'transparencia' as fonte,
    c.emenda_codigo,
    c.funcao,
    c.subfuncao,
    c.localidade,
    c.tipo,
    c.publicado_em,
    c.convenente,
    c.objeto,
    c.convenio_numero,
    c.valor,
    cast(k.capturado_em as date) as capturado_em

from {{ ref('stg_transparencia__emendas_convenios') }} as c

left join {{ ref('stg_metadata__captures') }} as k on k.source_file_id = c.source_file_id
