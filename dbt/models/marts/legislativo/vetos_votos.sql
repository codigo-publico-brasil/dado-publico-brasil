-- Voto nominal de deputados e senadores em cada dispositivo vetado votado, como a fonte entrega: nome, partido e UF,
-- sem o código do parlamentar. Por isso não é ligado a `pessoas` (ADR 0013). Uma linha por dispositivo e voto.
select
    '{{ var("source_senado") }}' as fonte,
    v.id_dispositivo,
    v.casa,
    v.nome_parlamentar,
    v.partido,
    v.uf,
    v.voto,
    v.sessao,
    cast(c.dt_captura as date) as dt_captura

from {{ ref('stg_senado__vetos_votos') }} as v

left join {{ ref('stg_metadata__captures') }} as c on c.id_captura = v.id_captura
