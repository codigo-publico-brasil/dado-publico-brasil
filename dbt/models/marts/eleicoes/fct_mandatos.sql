-- Um mandato por candidatura eleita (informada pelo TSE ou, em disputa de uma vaga que o TSE não fecha, derivada dos votos;
-- `base_eleicao` diz qual) (titular, vice e suplente eleito junto, de todos os cargos, inclusive vereador): o
-- mandato nasce da eleição, não do exercício. Quem assume depois como suplente é exercício (fct_exercicios).
-- Início, por ordem: (1) a regra da Constituição para o cargo, com a vigência por ano de eleição (dim_cargos_posse; derivado,
-- porque a data do TSE traz 1º de janeiro para deputados e senadores e posse de 2026 que não bate com a Constituição);
-- (2) deputado estadual e distrital: a posse que a constituição estadual (ou a norma da Assembleia) fixa, por UF e vigência
-- (dim_cargos_posse_uf, só as UFs com fonte conferida; derivado); (3) sem regra (vereador, UF sem fonte), a data de posse que o TSE informa na disputa, só se cai no
-- ano seguinte ao da eleição e a eleição não é a do ano corrente (o arquivo de vagas traz data provisória); fora disso o início
-- fica vazio e o teste mede a lacuna. A data original do TSE fica em dt_posse_tse. O fim é sempre derivado da duração do
-- mandato na Constituição.
-- `ano_inicio` é o ano da eleição (dim_eleicoes) mais um, mesmo sem data de posse. `tipo_mandato` compara o mandato com o
-- anterior da mesma pessoa no mesmo cargo (e na mesma unidade, abaixo do nível federal): reeleito se o anterior é da
-- eleição de um mandato atrás, retorno se há um intervalo, novato se não há anterior e a base de eleições já cobria o ciclo
-- anterior (senão fica vazio: sem prova nada é afirmado).
with mandatos as (

select
    'tse' as fonte,
    c.id_candidatura,
    c.id_disputa,
    d.id_eleicao,
    d.id_cargo,
    d.id_territorio,
    c.id_partido,
    c.id_pessoa_tse,
    c.id_pessoa,
    te.base_eleicao,
    d.dt_posse as dt_posse_tse,
    i.dt_inicio,
    i.base_dt_inicio,
    cast(i.dt_inicio + to_years(k.duracao_anos) - interval 1 day as date) as dt_fim_prevista,
    c.id_captura,
    c.dt_captura,
    el.ano_eleicao + 1 as ano_inicio,
    el.ano_eleicao,
    k.duracao_anos,
    k.esfera

from {{ ref('fct_candidaturas') }} as c

inner join {{ ref('int_tse_eleitos') }} as te on te.id_candidatura = c.id_candidatura

left join {{ ref('dim_disputas') }} as d on d.id_disputa = c.id_disputa

left join {{ ref('dim_eleicoes') }} as el on el.id_eleicao = d.id_eleicao

left join {{ ref('dim_cargos') }} as k on k.id_cargo = d.id_cargo

left join {{ ref('dim_cargos_posse') }} as p
    on p.id_cargo = d.id_cargo and el.ano_eleicao between p.ano_eleicao_de and p.ano_eleicao_ate

left join {{ ref('dim_cargos_posse_uf') }} as pu
    on pu.id_cargo = d.id_cargo and pu.id_territorio = d.id_territorio
    and el.ano_eleicao between pu.ano_eleicao_de and pu.ano_eleicao_ate

cross join lateral (
    select
        case
            when p.id_cargo is not null then make_date(el.ano_eleicao + 1, p.mes_posse, p.dia_posse)
            when pu.id_cargo is not null then make_date(el.ano_eleicao + 1, pu.mes_posse, pu.dia_posse)
            when year(d.dt_posse) = el.ano_eleicao + 1 and el.ano_eleicao < year(current_date) then d.dt_posse
        end as dt_inicio,
        case
            when p.id_cargo is not null or pu.id_cargo is not null then 'derivado'
            when year(d.dt_posse) = el.ano_eleicao + 1 and el.ano_eleicao < year(current_date) then 'informado'
        end as base_dt_inicio
) as i

),

anteriores as (

    select
        *,
        -- cada cargo conta à parte: quem foi titular e depois vice não é "reeleito"
        lag(ano_eleicao) over (
            partition by id_pessoa, id_cargo, if(esfera = 'federal', '', id_territorio) order by ano_eleicao
        ) as ano_anterior,
        min(ano_eleicao) filter (where id_pessoa is not null) over (partition by id_cargo) as primeiro_ano_do_cargo

    from mandatos

)

select
    * exclude (ano_eleicao, duracao_anos, esfera, ano_anterior, primeiro_ano_do_cargo),
    case
        when id_pessoa is null then null
        when ano_anterior is not null and ano_eleicao - ano_anterior = duracao_anos then 'reeleito'
        when ano_anterior is not null then 'retorno'
        when ano_eleicao - duracao_anos >= primeiro_ano_do_cargo then 'novato'
    end as tipo_mandato

from anteriores
