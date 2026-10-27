-- Eleitos para presidente, governador, senador, deputado federal, estadual e distrital (eleições gerais) e para prefeito e vereador
-- (eleições municipais): uma linha por eleito, de todos
-- os partidos e inclusive de quem ainda não é pessoa do projeto. O resultado é o que o TSE informa na data da
-- captura: provisório até a diplomação. Votos e percentual vêm da votação por município e zona, quando carregada.
-- O percentual é sobre os votos nominais válidos do cargo na unidade eleitoral (sem os votos de legenda).
-- `tipo_mandato` para quem foi eleito à Câmara ou ao Senado: reeleito (tinha mandato na mesma casa na
-- legislatura em curso na eleição), retorno (já teve mandato na mesma casa, antes) ou novato (pessoa ligada, sem mandato
-- na casa). Quem não é pessoa do projeto usa o histórico do TSE (a mesma pessoa em outras eleições, ADR 0025): reeleito
-- se foi eleito para o mesmo cargo na eleição anterior, retorno se foi eleito antes. Sem prova, fica sem tipo (nem novato).
with eleitos as (

    select
        c.*,
        case c.cargo
            when 'Deputado federal' then 'Câmara dos Deputados'
            when 'Senador' then 'Senado Federal'
        end as casa

    from {{ ref('stg_tse__candidaturas') }} as c

    where c.resultado like 'Eleito%'
        and c.cargo in ('Presidente', 'Governador', 'Senador', 'Deputado federal', 'Deputado estadual', 'Deputado distrital', 'Prefeito', 'Vereador')

    -- o TSE pode marcar "eleito" nos dois turnos (por exemplo, o governador de Goiás em 2014): vale o turno final
    qualify row_number() over (partition by c.id_candidatura order by c.turno desc) = 1

),

vitorias as (

    -- eleições ganhas por cada pessoa do TSE, por cargo, unidade eleitoral e ano

    select p.id_pessoa_tse, c.cargo, c.ue, c.ano_eleicao

    from {{ ref('stg_tse__candidaturas') }} as c

    inner join {{ ref('int_tse_pessoas') }} as p on p.id_candidatura = c.id_candidatura

    where c.resultado like 'Eleito%'

    group by all

),

votos as (

    select ano_eleicao, turno, cd_ue, cargo, id_candidatura, sum(votos_validos) as qtd_votos

    from {{ ref('stg_tse__votacao') }}

    group by all

),

totais as (

    select ano_eleicao, turno, cd_ue, cargo, sum(qtd_votos) as total_votos

    from votos

    group by all

),

historico as (

    -- eleito de novo (4 anos antes) ou de volta (antes disso) no mesmo cargo, pela mesma pessoa do TSE (ADR 0025)
    select
        e.id_candidatura,
        case
            when bool_or(w.ano_eleicao = e.ano_eleicao - 4) then 'reeleito'
            when bool_or(w.ano_eleicao < e.ano_eleicao - 4) then 'retorno'
        end as tipo

    from eleitos as e

    inner join {{ ref('int_tse_pessoas') }} as p on p.id_candidatura = e.id_candidatura

    inner join vitorias as w
        on w.id_pessoa_tse = p.id_pessoa_tse and w.cargo = e.cargo and w.ano_eleicao < e.ano_eleicao
        -- prefeito e vereador são de um município: quem foi eleito em outra cidade não é reeleito nem retorno nesta
        and (e.cargo not in ('Prefeito', 'Vereador') or w.ue = e.ue)

    group by e.id_candidatura

)

select
    '{{ var("source_tse") }}' as fonte,
    e.id_candidatura,
    e.ano_eleicao,
    e.turno,
    e.uf,
    e.ue,
    e.ue_nome,
    e.cargo,
    e.nome_urna,
    e.nome,
    e.partido_sigla as partido,
    e.situacao_candidatura,
    e.resultado,
    e.nome_social,
    e.grau_instrucao,
    e.estado_civil,
    e.ocupacao,
    e.uf_nascimento,
    e.coligacao_nome,
    e.coligacao_composicao,
    e.federacao_sigla,
    e.federacao_composicao,
    cast(v.qtd_votos as bigint) as qtd_votos,
    cast(round(100.0 * v.qtd_votos / nullif(t.total_votos, 0), 2) as decimal(5, 2)) as percentual_votos_nominais,
    i.id_pessoa,
    case
        -- cargos sem base de mandatos (presidente, governador, deputado estadual e distrital, prefeito, vereador) e quem
        -- não é pessoa do projeto: só a prova do histórico do TSE; sem prova fica sem tipo, nunca novato
        when e.casa is null or i.id_pessoa is null then h.tipo
        when exists (
            select 1 from {{ ref('mandatos') }} as m
            where m.id_pessoa = i.id_pessoa and m.casa = e.casa
                and m.dt_legislatura_inicio <= make_date(e.ano_eleicao, 10, 1)
                and m.dt_legislatura_fim >= make_date(e.ano_eleicao, 10, 1)
        ) then 'reeleito'
        when exists (
            select 1 from {{ ref('mandatos') }} as m
            where m.id_pessoa = i.id_pessoa and m.casa = e.casa
                and m.dt_legislatura_fim < make_date(e.ano_eleicao, 10, 1)
        ) then 'retorno'
        else 'novato'
    end as tipo_mandato,
    pt.id_pessoa_tse,
    i.metodo as vinculo_metodo,
    i.confirmado_por as vinculo_aprovado_por,
    cast(k.dt_captura as date) as dt_captura,
    'https://dadosabertos.tse.jus.br/dataset/candidatos-' || e.ano_eleicao as fonte_url

from eleitos as e

left join votos as v
    on v.id_candidatura = e.id_candidatura and v.turno = e.turno

left join totais as t
    on t.ano_eleicao = v.ano_eleicao and t.turno = v.turno and t.cd_ue = v.cd_ue and t.cargo = v.cargo

left join {{ ref('stg_identity__pessoa_identificadores') }} as i
    on i.fonte = '{{ var("source_tse") }}'
    and i.id_tipo = '{{ var("id_type_tse") }}'
    and i.id_na_fonte = e.id_candidatura

left join {{ ref('int_tse_pessoas') }} as pt on pt.id_candidatura = e.id_candidatura

left join historico as h on h.id_candidatura = e.id_candidatura

left join {{ ref('stg_metadata__captures') }} as k on k.id_captura = e.id_captura
