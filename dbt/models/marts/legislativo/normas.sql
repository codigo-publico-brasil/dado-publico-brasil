-- Catálogo das normas federais (leis, decretos, medidas provisórias, emendas...): só metadados. O texto integral
-- não vem desta fonte. Uma linha por norma, com o link da página oficial.
select
    '{{ var("source_senado") }}' as fonte,
    n.id_norma,
    n.tipo_sigla,
    n.tipo,
    n.numero,
    n.ano,
    n.dt_assinatura,
    n.nome,
    n.identificador,
    n.ementa,
    n.ementa_oficial,
    n.apelido,
    'https://legis.senado.leg.br/norma/' || n.id_norma as fonte_url,
    cast(c.dt_captura as date) as dt_captura

from {{ ref('stg_senado__normas') }} as n

left join {{ ref('stg_metadata__captures') }} as c on c.id_captura = n.id_captura
