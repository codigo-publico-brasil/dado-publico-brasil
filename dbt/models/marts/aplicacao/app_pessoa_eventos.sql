-- A ficha da pessoa com a linha do tempo: um evento por linha, com o nome do tipo, do cargo e do território e o endereço
-- do arquivo original da fonte. Só leitura de fct_eventos e do núcleo.
select
    e.id_evento,
    e.id_pessoa,
    e.ano_evento,
    e.dt_evento,
    tp.id_tipo_evento,
    tp.descricao as evento,
    c.nome as cargo,
    t.nome as territorio,
    pa.sigla as partido,
    e.base,
    cp.url as url_original

from {{ ref('fct_eventos') }} as e

inner join {{ ref('dim_evento_tipos') }} as tp on tp.id_tipo_evento = e.id_tipo_evento

left join {{ ref('dim_cargos') }} as c on c.id_cargo = e.id_cargo

left join {{ ref('dim_territorios') }} as t on t.id_territorio = e.id_territorio

left join {{ ref('dim_partidos') }} as pa on pa.id_partido = e.id_partido

left join {{ ref('stg_metadata__captures') }} as cp on cp.id_captura = e.id_captura
