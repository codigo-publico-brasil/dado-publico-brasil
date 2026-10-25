-- Votos de cada candidatura de quem já é pessoa do projeto, somados dos municípios e zonas, nas eleições carregadas.
-- Os votos por município e zona de todos os candidatos ficam no staging.
select
    '{{ var("source_tse") }}' as fonte,
    i.id_pessoa,
    v.id_candidatura,
    v.ano_eleicao,
    v.turno,
    any_value(v.uf) as uf,
    any_value(v.cargo) as cargo,
    cast(sum(v.votos_nominais) as bigint) as votos_nominais,
    cast(sum(v.votos_validos) as bigint) as votos_validos,
    count(distinct v.cd_municipio) as municipios,
    cast(max(k.dt_captura) as date) as dt_captura

from {{ ref('stg_tse__votacao') }} as v

inner join {{ ref('stg_identity__pessoa_identificadores') }} as i
    on i.fonte = '{{ var("source_tse") }}'
    and i.id_tipo = '{{ var("id_type_tse") }}'
    and i.id_na_fonte = v.id_candidatura

left join {{ ref('stg_metadata__captures') }} as k on k.id_captura = v.id_captura

group by i.id_pessoa, v.id_candidatura, v.ano_eleicao, v.turno
