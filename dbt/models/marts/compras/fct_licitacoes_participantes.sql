-- Participantes dos itens das licitações do governo federal, com a marca de vencedor, uma linha por item e participante como a
-- fonte publica. Participante pessoa física (CPF mascarado) fica marcado em `fl_contem_dado_pessoal`.
select
    'transparencia' as fonte,
    p.id_licitacao,
    p.cd_item,
    p.item,
    p.cd_participante,
    p.participante,
    p.fl_vencedor,
    coalesce(p.cd_participante like '%*%', false) as fl_contem_dado_pessoal,
    p.id_captura,
    cast(k.dt_captura as date) as dt_captura

from {{ ref('stg_transparencia__licitacoes_participantes') }} as p

left join {{ ref('stg_metadata__capturas') }} as k on k.id_captura = p.id_captura
