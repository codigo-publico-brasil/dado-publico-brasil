-- Cada dispositivo vetado: o texto que foi vetado, a razão do veto escrita pela Presidência e o que o Congresso
-- decidiu (situação como a fonte informa). Só dos vetos já buscados. Uma linha por dispositivo.
select
    '{{ var("source_senado") }}' as fonte,
    d.dispositivo_id,
    d.materia_veto_id,
    v.veto_id,
    d.identificador,
    d.descricao,
    d.texto_vetado,
    d.razao_veto,
    d.situacao,
    d.possui_votos,
    d.tipo_votacao,
    d.sessao_em,
    cast(c.capturado_em as date) as capturado_em

from {{ ref('stg_senado__vetos_dispositivos') }} as d

left join {{ ref('stg_senado__vetos') }} as v on v.materia_veto_id = d.materia_veto_id

left join {{ ref('stg_metadata__captures') }} as c on c.source_file_id = d.source_file_id
