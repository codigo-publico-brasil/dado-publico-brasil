-- Prefeito, vice e vereadores de cada município por eleição, com partido. Só leitura de fatos.mandatos e do núcleo.
select
    m.id_territorio,
    t.nome as municipio,
    e.ano_eleicao,
    c.nome as cargo,
    p.nome_publico as nome,
    pa.sigla as partido,
    m.id_pessoa

from {{ ref('fatos_mandatos') }} as m

inner join {{ ref('territorios') }} as t on t.id_territorio = m.id_territorio and t.tipo = 'municipio'

inner join {{ ref('eleicoes') }} as e on e.id_eleicao = m.id_eleicao

inner join {{ ref('cargos') }} as c on c.id_cargo = m.id_cargo

left join {{ ref('core_pessoas') }} as p on p.id_pessoa = m.id_pessoa

left join {{ ref('core_partidos') }} as pa on pa.id_partido = m.id_partido

where c.esfera = 'municipal'
