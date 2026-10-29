-- O voto de cada pessoa em cada votação nominal (Câmara e Senado), com a data, a descrição e o resultado da votação, tal como a
-- fonte publica. Uma linha por pessoa e votação; as proposições da votação estão em app_decisao. Só leitura dos fatos.
select
    v.fonte,
    v.id_votacao,
    v.id_pessoa,
    v.voto,
    v.dt_voto,
    pa.sigla as partido,
    v.partido_na_fonte,
    v.uf,
    vo.dt_votacao,
    vo.descricao,
    vo.aprovada

from {{ ref('fct_votos') }} as v

left join {{ ref('fct_votacoes') }} as vo on vo.fonte = v.fonte and vo.id_votacao = v.id_votacao

left join {{ ref('dim_partidos') }} as pa on pa.id_partido = v.id_partido
