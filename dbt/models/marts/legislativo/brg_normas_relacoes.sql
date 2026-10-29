-- O que cada norma tem de ligação com atos posteriores, como o Senado declara: alteração, regulamentação, veto,
-- declaração de constitucionalidade etc. Só das normas detalhadas (leis, leis complementares, emendas, medidas
-- provisórias e a Constituição). Uma linha por norma, ato posterior e tipo de relação.
select
    '{{ var("source_senado") }}' as fonte,
    r.id_norma,
    r.tipo_relacao,
    r.id_norma_posterior,
    r.norma_posterior_nome,
    r.dt_norma_posterior_assinatura,
    r.dt_publicacao,
    r.publicacao,
    cast(c.dt_captura as date) as dt_captura

from {{ ref('stg_senado__normas_relacoes') }} as r

left join {{ ref('stg_metadata__captures') }} as c on c.id_captura = r.id_captura
