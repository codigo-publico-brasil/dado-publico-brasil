-- Ponte entre licitações e os empenhos relacionados a elas, como o Portal da Transparência publica.
select
    'transparencia' as fonte,
    e.id_licitacao,
    e.cd_empenho,
    e.dt_emissao,
    e.observacao,
    e.valor,
    e.id_captura,
    cast(k.dt_captura as date) as dt_captura

from {{ ref('stg_transparencia__licitacoes_empenhos') }} as e

left join {{ ref('stg_metadata__capturas') }} as k on k.id_captura = e.id_captura
