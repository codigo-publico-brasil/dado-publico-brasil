-- Quem ocupa cada cargo, uma linha por mandato; o aplicativo filtra a data (dt_inicio <= data <= dt_fim_prevista) e o cargo.
-- Só leitura dos fatos e do núcleo: nenhuma regra de negócio aqui. A composição eleita não é o exercício (cassação,
-- renúncia e morte não entram no fim); para quem de fato exerce, ver agg_composicoes e fct_exercicios.
select
    m.id_candidatura,
    m.id_pessoa,
    p.nome_publico as nome,
    c.nome as cargo,
    t.nome as territorio,
    pa.sigla as partido,
    m.dt_inicio,
    m.base_dt_inicio as base_do_inicio,
    m.dt_fim_prevista,
    m.base_eleicao

from {{ ref('fct_mandatos') }} as m

inner join {{ ref('dim_pessoas') }} as p on p.id_pessoa = m.id_pessoa

inner join {{ ref('dim_cargos') }} as c on c.id_cargo = m.id_cargo

left join {{ ref('dim_territorios') }} as t on t.id_territorio = m.id_territorio

left join {{ ref('dim_partidos') }} as pa on pa.id_partido = m.id_partido

where m.dt_inicio is not null
