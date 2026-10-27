-- Eleições do arquivo de vagas do TSE, uma por ano e código do TSE. O arquivo mistura as eleições ordinárias com as
-- suplementares e as renovadas, e o nome delas não permite separar (há "Nova eleição", "Majoritária - Criciúma", "Sup."...).
-- A regra é nossa e fica marcada: em cada ano e cargo, a eleição ordinária é o código do TSE que cobre mais unidades
-- eleitorais; um código é ordinário se vencer em algum cargo do ano. É a mesma regra que já valia em eleitos_cargos.
with vagas as (

    select * from {{ ref('stg_tse__vagas') }}

),

cobertura as (

    select ano_eleicao, cd_cargo, cd_eleicao, count(distinct ue) as unidades

    from vagas

    group by all

),

ordinarias as (

    select distinct ano_eleicao, cd_eleicao

    from cobertura

    qualify row_number() over (partition by ano_eleicao, cd_cargo order by unidades desc, cd_eleicao) = 1

)

select
    'tse' as fonte,
    cast(v.ano_eleicao as varchar) || '-' || cast(v.cd_eleicao as varchar) as id_eleicao,
    v.ano_eleicao,
    v.cd_eleicao,
    any_value(v.eleicao) as nome,
    o.cd_eleicao is not null as fl_ordinaria,
    max(v.id_captura) as id_captura

from vagas as v

left join ordinarias as o on o.ano_eleicao = v.ano_eleicao and o.cd_eleicao = v.cd_eleicao

group by v.ano_eleicao, v.cd_eleicao, o.cd_eleicao
