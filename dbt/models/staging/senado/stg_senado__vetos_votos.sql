-- Voto nominal de cada deputado e senador num dispositivo vetado. A fonte entrega nome, partido e UF, sem o
-- código do parlamentar: por isso o voto não é ligado a uma pessoa (ADR 0013).
with votacoes as (

    select * from {{ source('senado', 'vetos_votos') }}

),

votos as (

    select 'Câmara' as casa, * from {{ source('senado', 'vetos_votos__camara_voto') }}

    union all by name

    select 'Senado' as casa, * from {{ source('senado', 'vetos_votos__senado_voto') }}

)

select
    try_cast(v._item as bigint) as dispositivo_id,
    o.casa,
    proper_name(o.nome_parlamentar) as nome_parlamentar,
    o.partido_parlamentar as partido,
    o.uf_parlamentar as uf,
    o.tipo_voto as voto,
    v.sessao,
    v._source_file_id as source_file_id

from votos as o

inner join votacoes as v on v._dlt_id = o._dlt_parent_id
