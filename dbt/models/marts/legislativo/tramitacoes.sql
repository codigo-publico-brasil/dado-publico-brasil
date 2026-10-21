select
    '{{ var("source_camara") }}' as fonte,
    cast(t.proposicao_id as varchar) as proposicao_id,
    t.sequencia,
    t.registrada_em,
    t.orgao_sigla,
    t.regime,
    t.descricao,
    t.situacao,
    t.despacho,
    cast(c.capturado_em as date) as capturado_em

from {{ ref('stg_camara__tramitacoes') }} as t

left join {{ ref('stg_metadata__captures') }} as c on c.source_file_id = t.source_file_id
