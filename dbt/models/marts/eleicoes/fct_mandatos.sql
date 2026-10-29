-- Um mandato por candidatura eleita (informada pelo TSE ou, em disputa de uma vaga que o TSE não fecha, derivada dos votos;
-- `base_eleicao` diz qual) (titular, vice e suplente eleito junto, de todos os cargos, inclusive vereador): o
-- mandato nasce da eleição, não do exercício. Quem assume depois como suplente é exercício (fct_exercicios).
-- Início, por ordem: (1) a regra da Constituição para o cargo, com a vigência por ano de eleição (dim_cargos_posse; derivado,
-- porque a data do TSE traz 1º de janeiro para deputados e senadores e posse de 2026 que não bate com a Constituição);
-- (2) sem regra na Constituição (vereador, deputado estadual), a data de posse que o TSE informa na disputa, só se cai no
-- ano seguinte ao da eleição e a eleição não é a do ano corrente (o arquivo de vagas traz data provisória); fora disso o início
-- fica vazio e o teste mede a lacuna. A data original do TSE fica em dt_posse_tse. O fim é sempre derivado da duração do
-- mandato na Constituição.
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
    e.base_eleicao,
    d.dt_posse as dt_posse_tse,
    i.dt_inicio,
    i.base_dt_inicio,
    cast(i.dt_inicio + to_years(k.duracao_anos) - interval 1 day as date) as dt_fim_prevista,
    c.id_captura

from {{ ref('fct_candidaturas') }} as c

inner join {{ ref('int_tse_eleitos') }} as e on e.id_candidatura = c.id_candidatura

left join {{ ref('dim_disputas') }} as d on d.id_disputa = c.id_disputa

left join {{ ref('dim_eleicoes') }} as e on e.id_eleicao = d.id_eleicao

left join {{ ref('dim_cargos') }} as k on k.id_cargo = d.id_cargo

left join {{ ref('dim_cargos_posse') }} as p
    on p.id_cargo = d.id_cargo and e.ano_eleicao between p.ano_eleicao_de and p.ano_eleicao_ate

cross join lateral (
    select
        case
            when p.id_cargo is not null then make_date(e.ano_eleicao + 1, p.mes_posse, p.dia_posse)
            when year(d.dt_posse) = e.ano_eleicao + 1 and e.ano_eleicao < year(current_date) then d.dt_posse
        end as dt_inicio,
        case
            when p.id_cargo is not null then 'derivado'
            when year(d.dt_posse) = e.ano_eleicao + 1 and e.ano_eleicao < year(current_date) then 'informado'
        end as base_dt_inicio
) as i

