-- Todas as candidaturas da pessoa, com foto, resultado e campanha, tenha ela vencido ou não. Só leitura dos fatos.
-- `fl_eleito` vale também para o vencedor derivado pela regra da Constituição quando o TSE não informa o resultado (por
-- exemplo, o 2º turno de presidente de 2006); `base_eleito` diz de onde vem, e `resultado` segue como o TSE informa.
select
    ca.id_candidatura,
    ca.id_pessoa,
    a.ano_eleicao,
    c.nome as cargo,
    ca.numero,
    pa.sigla as partido,
    ca.resultado,
    case when e.id_candidatura is not null then true else ca.fl_eleito end as fl_eleito,
    e.base_eleicao as base_eleito,
    ca.foto_caminho,
    cm.valor_receitas,
    cm.valor_despesas,
    cm.valor_bens,
    cap.url as fonte_url,
    cast(cap.dt_captura as date) as dt_captura,
    cr.url as fonte_url_receitas,
    cd.url as fonte_url_despesas,
    cb.url as fonte_url_bens,
    cast(greatest(cr.dt_captura, cd.dt_captura, cb.dt_captura) as date) as dt_captura_campanha

from {{ ref('fct_candidaturas') }} as ca

inner join (select distinct id_candidatura, ano_eleicao from {{ ref('stg_tse__candidaturas') }}) as a
    on a.id_candidatura = ca.id_candidatura

left join {{ ref('dim_disputas') }} as d on d.id_disputa = ca.id_disputa

left join {{ ref('dim_cargos') }} as c on c.id_cargo = d.id_cargo

left join {{ ref('int_tse_eleitos') }} as e on e.id_candidatura = ca.id_candidatura

left join {{ ref('fct_campanhas') }} as cm on cm.id_candidatura = ca.id_candidatura

left join {{ ref('dim_partidos') }} as pa on pa.id_partido = ca.id_partido

left join {{ ref('stg_metadata__captures') }} as cap on cap.id_captura = ca.id_captura

left join {{ ref('stg_metadata__captures') }} as cr on cr.id_captura = cm.id_captura_receitas

left join {{ ref('stg_metadata__captures') }} as cd on cd.id_captura = cm.id_captura_despesas

left join {{ ref('stg_metadata__captures') }} as cb on cb.id_captura = cm.id_captura_bens

where ca.id_pessoa is not null
