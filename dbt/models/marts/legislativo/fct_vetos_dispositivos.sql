-- Cada dispositivo vetado: o texto que foi vetado, a razão do veto escrita pela Presidência e o que o Congresso
-- decidiu (situação como a fonte informa). Só dos vetos já buscados. Uma linha por dispositivo.
select
    '{{ var("source_senado") }}' as fonte,
    d.id_dispositivo,
    d.id_materia_veto,
    v.id_veto,
    d.identificador,
    d.descricao,
    d.texto_vetado,
    d.razao_veto,
    d.situacao,
    d.fl_possui_votos,
    d.tipo_votacao,
    d.dt_sessao,
    cast(c.dt_captura as date) as dt_captura

from {{ ref('stg_senado__vetos_dispositivos') }} as d

left join {{ ref('stg_senado__vetos') }} as v on v.id_materia_veto = d.id_materia_veto

left join {{ ref('stg_metadata__captures') }} as c on c.id_captura = d.id_captura
