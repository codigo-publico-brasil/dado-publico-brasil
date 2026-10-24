-- Quem recebeu o dinheiro de cada emenda, por mês, como o Portal da Transparência publica. Inclui pessoa física
-- (cidadão comum, com CPF mascarado): `contem_dado_pessoal` marca essas linhas para quem consome decidir como mostrá-las.
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
    (
        f.favorecido_codigo like '%*%'
        or lower(f.tipo_favorecido) like 'pessoa f%'
        or f.tipo_favorecido like 'Inscri%'
    ) as contem_dado_pessoal,
    cast(k.capturado_em as date) as capturado_em

from {{ ref('stg_transparencia__emendas_favorecidos') }} as f

left join {{ ref('stg_metadata__captures') }} as k on k.source_file_id = f.source_file_id
