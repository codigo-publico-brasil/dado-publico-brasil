-- Os partidos da pessoa ao longo do tempo, de fontes oficiais (histórico da Câmara, votos, início da legislatura e candidaturas
-- do TSE), com a base de cada período. Uma linha por pessoa e período. Só leitura dos fatos e do núcleo.
select
    f.id_pessoa_partido,
    f.id_pessoa,
    pa.sigla as partido,
    f.partido_na_fonte,
    f.ano_referencia,
    f.dt_inicio,
    f.dt_ultimo_registro,
    f.base,
    f.fl_mais_recente

from {{ ref('fct_pessoas_partidos') }} as f

left join {{ ref('dim_partidos') }} as pa on pa.id_partido = f.id_partido
