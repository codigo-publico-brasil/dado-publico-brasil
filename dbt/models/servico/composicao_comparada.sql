-- A composição por corte, tipo, cargo, território e partido, com nomes legíveis; o aplicativo escolhe dois cortes e compara.
-- Só leitura de analise.composicoes. A eleita e a em exercício aparecem separadas.
select
    c.dt_corte,
    c.tipo_composicao,
    ca.nome as cargo,
    t.nome as territorio,
    pa.sigla as partido,
    c.qtd_membros as cadeiras

from {{ ref('analise_composicoes') }} as c

inner join {{ ref('cargos') }} as ca on ca.id_cargo = c.id_cargo

left join {{ ref('territorios') }} as t on t.id_territorio = c.id_territorio

left join {{ ref('core_partidos') }} as pa on pa.id_partido = c.id_partido
