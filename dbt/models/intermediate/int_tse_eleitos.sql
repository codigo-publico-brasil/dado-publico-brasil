-- Quem foi eleito, com a base de cada eleição. Entrada da identidade e de fct_mandatos.
--  - informado: o arquivo de candidaturas do TSE diz "Eleito" (em algum turno).
--  - derivado: o TSE não diz quem venceu uma disputa de UMA vaga (presidente, governador, prefeito) de eleição já passada
--    (em 2006 o TSE não informa o vencedor do 2º turno de presidente), e então vale a regra da Constituição: vence quem
--    tem mais votos válidos no último turno (art. 77, § 3º; art. 28; art. 29, II). Só com candidatura apta ou deferida,
--    sem empate e sem nenhum eleito informado na disputa. A eleição do ano corrente fica de fora: o resultado pode ainda
--    não estar fechado no arquivo do TSE.
with informados as (

    select distinct id_candidatura, ano_eleicao, ue, cargo

    from {{ ref('stg_tse__candidaturas') }}

    where resultado like 'Eleito%'

),

votos_turno as (

    select
        id_candidatura,
        ano_eleicao,
        cd_ue as ue,
        cargo,
        turno,
        sum(votos_validos) as votos,
        any_value(situacao_candidatura) as situacao_candidatura

    from {{ ref('stg_tse__votacao') }}

    where cargo in ('Presidente', 'Governador', 'Prefeito')
        and ano_eleicao < year(current_date)

    group by id_candidatura, ano_eleicao, cd_ue, cargo, turno

),

ultimo_turno as (

    select
        *,
        row_number() over (partition by ano_eleicao, ue, cargo order by votos desc) as posicao,
        lead(votos) over (partition by ano_eleicao, ue, cargo order by votos desc) as votos_do_segundo

    from votos_turno

    qualify turno = max(turno) over (partition by ano_eleicao, ue, cargo)

),

derivados as (

    select u.id_candidatura

    from ultimo_turno as u

    where u.posicao = 1
        and u.votos > coalesce(u.votos_do_segundo, 0)
        and u.situacao_candidatura in ('Apto', 'Deferido')
        and not exists (
            select 1 from informados as i where i.ano_eleicao = u.ano_eleicao and i.ue = u.ue and i.cargo = u.cargo
        )

)

select id_candidatura, 'informado' as base_eleicao from informados

union all

select id_candidatura, 'derivado' from derivados
