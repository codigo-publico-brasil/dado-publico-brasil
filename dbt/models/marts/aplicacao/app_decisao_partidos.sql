-- O voto por partido em cada votação, com o partido como chave (`id_partido`) e a sigla do voto ao lado. Só leitura de
-- fct_votos e do núcleo.
select
    v.fonte,
    v.id_votacao,
    v.id_partido,
    coalesce(pa.sigla, v.partido_na_fonte) as partido,
    v.partido_na_fonte as partido_no_voto,
    v.voto,
    count(*) as qtd_votos

from {{ ref('fct_votos') }} as v

left join {{ ref('dim_partidos') }} as pa on pa.id_partido = v.id_partido

group by v.fonte, v.id_votacao, v.id_partido, pa.sigla, v.partido_na_fonte, v.voto
