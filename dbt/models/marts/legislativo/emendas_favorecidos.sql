-- Quem recebeu o dinheiro de cada emenda, por mês, como o Portal da Transparência publica. Inclui pessoa física
-- (cidadão comum, com CPF mascarado): `contem_dado_pessoal` marca essas linhas para quem consome decidir como mostrá-las.
select
    'transparencia' as fonte,
    f.cd_emenda,
    f.cd_autor,
    f.autor_nome,
    f.numero,
    f.tipo,
    f.ano,
    f.mes,
    f.cd_favorecido,
    f.favorecido,
    f.natureza_juridica,
    f.tipo_favorecido,
    f.uf,
    f.municipio,
    f.valor,
    (
        f.cd_favorecido like '%*%'
        or lower(f.tipo_favorecido) like 'pessoa f%'
        or f.tipo_favorecido like 'Inscri%'
    ) as fl_contem_dado_pessoal,
    cast(k.dt_captura as date) as dt_captura

from {{ ref('stg_transparencia__emendas_favorecidos') }} as f

left join {{ ref('stg_metadata__captures') }} as k on k.id_captura = f.id_captura
