-- Votos de cada candidatura de quem já é pessoa do projeto, somados dos municípios e zonas, nas eleições carregadas.
-- Os votos por município e zona de todos os candidatos ficam no staging.
select
    '{{ var("source_tse") }}' as fonte,
    i.id_pessoa,
    v.candidatura_id,
    v.ano_eleicao,
    v.turno,
    any_value(v.uf) as uf,
    any_value(v.cargo) as cargo,
    cast(sum(v.votos_nominais) as bigint) as votos_nominais,
    cast(sum(v.votos_validos) as bigint) as votos_validos,
    count(distinct v.municipio_codigo) as municipios,
    cast(max(k.capturado_em) as date) as capturado_em

from {{ ref('stg_tse__votacao') }} as v

inner join {{ ref('stg_identity__pessoa_identificadores') }} as i
    on i.fonte = '{{ var("source_tse") }}'
    and i.tipo_id = '{{ var("id_type_tse") }}'
    and i.id_na_fonte = v.candidatura_id

left join {{ ref('stg_metadata__captures') }} as k on k.source_file_id = v.source_file_id

group by i.id_pessoa, v.candidatura_id, v.ano_eleicao, v.turno
