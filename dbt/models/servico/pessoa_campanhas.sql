-- Todas as candidaturas da pessoa, com foto, resultado e campanha, tenha ela vencido ou não. Só leitura dos fatos.
select
    ca.id_candidatura,
    ca.id_pessoa,
    a.ano_eleicao,
    c.nome as cargo,
    ca.numero,
    pa.sigla as partido,
    ca.resultado,
    ca.fl_eleito,
    ca.foto_caminho,
    cm.valor_receitas,
    cm.valor_despesas,
    cm.valor_bens

from {{ ref('fatos_candidaturas') }} as ca

inner join (select distinct id_candidatura, ano_eleicao from {{ ref('stg_tse__candidaturas') }}) as a
    on a.id_candidatura = ca.id_candidatura

left join {{ ref('disputas') }} as d on d.id_disputa = ca.id_disputa

left join {{ ref('cargos') }} as c on c.id_cargo = d.id_cargo

left join {{ ref('campanhas') }} as cm on cm.id_candidatura = ca.id_candidatura

left join {{ ref('core_partidos') }} as pa on pa.id_partido = ca.id_partido

where ca.id_pessoa is not null
