-- Onde cada norma foi publicada no Diário Oficial (a publicação original e, por exemplo, a do veto), com página e
-- coluna. Só das normas detalhadas. Uma linha por norma e publicação.
select
    '{{ var("source_senado") }}' as fonte,
    p.norma_id,
    p.publicacao_id,
    p.tipo_sigla,
    p.veiculo,
    p.publicada_em,
    p.pagina,
    p.coluna,
    p.tem_texto,
    cast(c.capturado_em as date) as capturado_em

from {{ ref('stg_senado__normas_publicacoes') }} as p

left join {{ ref('stg_metadata__captures') }} as c on c.source_file_id = p.source_file_id
