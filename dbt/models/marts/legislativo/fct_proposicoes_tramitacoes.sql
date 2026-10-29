select
    '{{ var("source_camara") }}' as fonte,
    cast(t.id_proposicao as varchar) as id_proposicao,
    t.sequencia,
    t.dt_registro,
    t.orgao_sigla,
    t.regime,
    t.descricao,
    t.situacao,
    t.despacho,
    cast(c.dt_captura as date) as dt_captura

from {{ ref('stg_camara__tramitacoes') }} as t

left join {{ ref('stg_metadata__captures') }} as c on c.id_captura = t.id_captura
