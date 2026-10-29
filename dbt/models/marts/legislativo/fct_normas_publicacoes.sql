-- Onde cada norma foi publicada no Diário Oficial (a publicação original e, por exemplo, a do veto), com página e
-- coluna. Só das normas detalhadas. Uma linha por norma e publicação.
select
    '{{ var("source_senado") }}' as fonte,
    p.id_norma,
    p.id_publicacao,
    p.tipo_sigla,
    p.veiculo,
    p.dt_publicacao,
    p.pagina,
    p.coluna,
    p.fl_tem_texto,
    cast(c.dt_captura as date) as dt_captura

from {{ ref('stg_senado__normas_publicacoes') }} as p

left join {{ ref('stg_metadata__captures') }} as c on c.id_captura = p.id_captura
