-- Todas as candidaturas da pessoa, com foto, resultado e campanha, tenha ela vencido ou não. Join puro sobre os marts.
-- `fl_eleito` vale também para o vencedor derivado pela regra da Constituição quando o TSE não informa o resultado (por
-- exemplo, o 2º turno de presidente de 2006); `base_eleito` (base_eleicao de fct_candidaturas, o mesmo conjunto de
-- fct_mandatos) diz de onde vem, e `resultado` segue como o TSE informa. Os endereços vêm de metadata.capturas.
select
    ca.id_candidatura,
    ca.id_pessoa,
    el.ano_eleicao,
    c.nome as cargo,
    ca.dt_eleicao,
    ca.numero,
    pa.sigla as partido,
    ca.resultado,
    case when ca.base_eleicao is not null then true else ca.fl_eleito end as fl_eleito,
    ca.base_eleicao as base_eleito,
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

left join {{ ref('dim_eleicoes') }} as el on el.id_eleicao = ca.id_eleicao

left join {{ ref('dim_disputas') }} as d on d.id_disputa = ca.id_disputa

left join {{ ref('dim_cargos') }} as c on c.id_cargo = d.id_cargo

left join {{ ref('fct_campanhas') }} as cm on cm.id_candidatura = ca.id_candidatura

left join {{ ref('dim_partidos') }} as pa on pa.id_partido = ca.id_partido

left join {{ source('metadata', 'capturas') }} as cap on cap.id_captura = ca.id_captura

left join {{ source('metadata', 'capturas') }} as cr on cr.id_captura = cm.id_captura_receitas

left join {{ source('metadata', 'capturas') }} as cd on cd.id_captura = cm.id_captura_despesas

left join {{ source('metadata', 'capturas') }} as cb on cb.id_captura = cm.id_captura_bens

where ca.id_pessoa is not null
