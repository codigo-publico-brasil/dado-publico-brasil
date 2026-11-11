-- Itens das licitações do governo federal, com o vencedor, uma linha por item e vencedor como a fonte publica. Vencedor pessoa
-- física (CPF mascarado) fica marcado em `fl_contem_dado_pessoal` para quem consome decidir como mostrar.
select
    'transparencia' as fonte,
    i.id_licitacao,
    i.cd_item,
    i.item,
    i.quantidade,
    i.valor,
    i.cd_vencedor,
    i.vencedor,
    coalesce(i.cd_vencedor like '%*%', false) as fl_contem_dado_pessoal,
    i.id_captura,
    cast(k.dt_captura as date) as dt_captura

from {{ ref('stg_transparencia__licitacoes_itens') }} as i

left join {{ ref('stg_metadata__capturas') }} as k on k.id_captura = i.id_captura
