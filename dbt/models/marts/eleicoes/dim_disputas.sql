-- Disputas: o cargo em uma unidade eleitoral de uma eleição, com o número de vagas que o TSE informa. É a base das
-- candidaturas e dos resultados. `ue` guarda a unidade como o TSE publica; `id_territorio` liga ao IBGE e fica vazio
-- onde o código do município do TSE não liga a um só município (a lacuna é medida por teste).
select
    'tse' as fonte,
    cast(v.ano_eleicao as varchar) || '-' || cast(v.cd_eleicao as varchar) || '-' || cast(v.cd_cargo as varchar) || '-' || v.ue as id_disputa,
    cast(v.ano_eleicao as varchar) || '-' || cast(v.cd_eleicao as varchar) as id_eleicao,
    c.id_cargo,
    coalesce(m.id_territorio, u.id_territorio, p.id_territorio) as id_territorio,
    v.ue,
    v.ue_nome,
    v.qtd_vagas,
    v.dt_posse,
    v.id_captura

from {{ ref('stg_tse__vagas') }} as v

inner join {{ ref('dim_cargos') }} as c on c.cd_cargo_tse = v.cd_cargo

left join {{ ref('dim_territorios') }} as m on m.tipo = 'municipio' and m.cd_municipio_tse = v.ue

left join {{ ref('dim_territorios') }} as u on u.tipo = 'uf' and u.sigla = v.ue

left join {{ ref('dim_territorios') }} as p on p.tipo = 'pais' and v.ue = 'BR'
