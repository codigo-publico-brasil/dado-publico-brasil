-- Catálogo das normas federais (leis, decretos, medidas provisórias, emendas...): só metadados. O texto integral
-- não vem desta fonte. Uma linha por norma, com o link da página oficial.
select
    '{{ var("source_senado") }}' as fonte,
    n.norma_id,
    n.tipo_sigla,
    n.tipo,
    n.numero,
    n.ano,
    n.assinada_em,
    n.nome,
    n.identificador,
    n.ementa,
    n.ementa_oficial,
    n.apelido,
    'https://legis.senado.leg.br/norma/' || n.norma_id as fonte_url,
    cast(c.capturado_em as date) as capturado_em

from {{ ref('stg_senado__normas') }} as n

left join {{ ref('stg_metadata__captures') }} as c on c.source_file_id = n.source_file_id
