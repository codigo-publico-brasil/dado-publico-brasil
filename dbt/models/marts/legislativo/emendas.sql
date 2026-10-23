-- Emendas parlamentares ao orçamento, como o Portal da Transparência publica: uma linha por emenda, localidade, função,
-- programa e ação, com os valores empenhado, liquidado e pago. O autor vem pelo nome e pelo código orçamentário, que
-- não é o código do parlamentar na Câmara ou no Senado: por isso a emenda não é ligada a `pessoas`.
select
    'transparencia' as fonte,
    e.emenda_codigo,
    e.ano,
    e.tipo,
    e.autor_codigo,
    e.autor_nome,
    e.numero,
    e.localidade,
    e.municipio_ibge,
    e.municipio,
    e.uf,
    e.regiao,
    e.funcao,
    e.subfuncao,
    e.programa_codigo,
    e.programa,
    e.acao_codigo,
    e.acao,
    e.plano_orcamentario,
    e.valor_empenhado,
    e.valor_liquidado,
    e.valor_pago,
    e.valor_restos_a_pagar_inscritos,
    e.valor_restos_a_pagar_cancelados,
    e.valor_restos_a_pagar_pagos,
    cast(k.capturado_em as date) as capturado_em

from {{ ref('stg_transparencia__emendas') }} as e

left join {{ ref('stg_metadata__captures') }} as k on k.source_file_id = e.source_file_id
