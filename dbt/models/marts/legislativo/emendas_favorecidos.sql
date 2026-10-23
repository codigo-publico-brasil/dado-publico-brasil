-- Quem recebeu o dinheiro de cada emenda, por mês: só pessoa jurídica e unidade gestora (a pessoa física, cidadão comum,
-- nunca entra). Uma linha por emenda, favorecido e mês.
select
    'transparencia' as fonte,
    f.emenda_codigo,
    f.autor_codigo,
    f.autor_nome,
    f.numero,
    f.tipo,
    f.ano,
    f.mes,
    f.favorecido_codigo,
    f.favorecido,
    f.natureza_juridica,
    f.tipo_favorecido,
    f.uf,
    f.municipio,
    f.valor,
    cast(k.capturado_em as date) as capturado_em

from {{ ref('stg_transparencia__emendas_favorecidos') }} as f

left join {{ ref('stg_metadata__captures') }} as k on k.source_file_id = f.source_file_id
