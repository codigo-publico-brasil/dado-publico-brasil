-- Situação de cada cargo em cada unidade eleitoral: quantas vagas existem, quantas já têm eleito e o que falta. Mostra o
-- estado real: o cargo sem todos os eleitos fica `aguardando_resultado` (por exemplo, governador no 2º turno), nunca
-- um palpite. `eleito_provisorio` quer dizer que todas as vagas têm eleito pelo resultado do TSE, ainda sem diplomação.
with vagas as (

    -- o arquivo de vagas também traz as eleições suplementares e renovadas do ano, com outro `cd_eleicao`: em cada ano,
    -- unidade e cargo vale o código que cobre mais unidades (a ordinária cobre milhares; a suplementar, uma ou duas)
    select v.*

    from {{ ref('stg_tse__vagas') }} as v

    left join (
        select ano_eleicao, cargo, cd_eleicao, count(distinct ue) as unidades
        from {{ ref('stg_tse__vagas') }}
        group by all
    ) as c
        on c.ano_eleicao = v.ano_eleicao and c.cargo = v.cargo and c.cd_eleicao is not distinct from v.cd_eleicao

    qualify dense_rank() over (
        partition by v.ano_eleicao, v.ue, v.cargo order by c.unidades desc nulls last, v.cd_eleicao
    ) = 1

),

eleitos_por_cargo as (

    select ano_eleicao, ue, cargo, count(distinct id_candidatura) as qtd_eleitos

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
    v.ue,
    v.ue_nome,
    v.cargo,
    v.qtd_vagas,
    coalesce(e.qtd_eleitos, 0) as qtd_eleitos,
    greatest(v.qtd_vagas - coalesce(e.qtd_eleitos, 0), 0) as qtd_pendentes,
    if(coalesce(e.qtd_eleitos, 0) >= v.qtd_vagas, 'eleito_provisorio', 'aguardando_resultado') as status,
    v.dt_posse,
    k.dt_captura,
    'https://dadosabertos.tse.jus.br/dataset/candidatos-' || v.ano_eleicao as fonte_url

from vagas as v

left join eleitos_por_cargo as e
    on e.ano_eleicao = v.ano_eleicao and e.ue = v.ue and e.cargo = v.cargo

left join capturas as k on k.ano_eleicao = v.ano_eleicao

where v.cargo in ('Presidente', 'Governador', 'Senador', 'Deputado federal', 'Deputado estadual', 'Deputado distrital', 'Prefeito', 'Vereador')
    and v.eleicao not ilike '%suplementar%'  -- só as eleições ordinárias; as suplementares e renovadas não entram aqui
