-- O que cada norma tem de ligação com atos posteriores, como o Senado declara: alteração, regulamentação, veto,
-- declaração de constitucionalidade etc. Só das normas detalhadas (leis, leis complementares, emendas, medidas
-- provisórias e a Constituição). Uma linha por norma, ato posterior e tipo de relação.
select
    '{{ var("source_senado") }}' as fonte,
    r.norma_id,
    r.tipo_relacao,
    r.norma_posterior_id,
    r.norma_posterior_nome,
    r.norma_posterior_assinada_em,
    r.publicada_em,
    r.publicacao,
    cast(c.capturado_em as date) as capturado_em

from {{ ref('stg_senado__normas_relacoes') }} as r

left join {{ ref('stg_metadata__captures') }} as c on c.source_file_id = r.source_file_id
