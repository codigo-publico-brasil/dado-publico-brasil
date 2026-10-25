-- Situação de cada cargo em cada unidade eleitoral: quantas vagas existem, quantas já têm eleito e o que falta. Mostra o
-- estado real: o cargo sem todos os eleitos fica `aguardando_resultado` (por exemplo, governador no 2º turno), nunca
-- um palpite. `eleito_provisorio` quer dizer que todas as vagas têm eleito pelo resultado do TSE, ainda sem diplomação.
with eleitos_por_cargo as (

    select ano_eleicao, uf, cargo, count(distinct id_candidatura) as qtd_eleitos

    from {{ ref('eleitos') }}

    group by all

),

capturas as (

    select c.ano_eleicao, max(cast(k.dt_captura as date)) as dt_captura

    from {{ ref('stg_tse__candidaturas') }} as c

    inner join {{ ref('stg_metadata__captures') }} as k on k.id_captura = c.id_captura

    group by c.ano_eleicao

)

select
    '{{ var("source_tse") }}' as fonte,
    v.ano_eleicao,
    v.uf,
    v.cargo,
    v.qtd_vagas,
    coalesce(e.qtd_eleitos, 0) as qtd_eleitos,
    greatest(v.qtd_vagas - coalesce(e.qtd_eleitos, 0), 0) as qtd_pendentes,
    if(coalesce(e.qtd_eleitos, 0) >= v.qtd_vagas, 'eleito_provisorio', 'aguardando_resultado') as status,
    v.dt_posse,
    k.dt_captura,
    'https://dadosabertos.tse.jus.br/dataset/candidatos-' || v.ano_eleicao as fonte_url

from {{ ref('stg_tse__vagas') }} as v

left join eleitos_por_cargo as e
    on e.ano_eleicao = v.ano_eleicao and e.uf = v.uf and e.cargo = v.cargo

left join capturas as k on k.ano_eleicao = v.ano_eleicao

where v.cargo in ('Presidente', 'Governador', 'Senador', 'Deputado federal')
    and v.eleicao not ilike '%suplementar%'  -- só as eleições gerais; as suplementares não entram aqui
