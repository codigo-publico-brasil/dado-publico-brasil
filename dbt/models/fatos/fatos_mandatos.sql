-- Um mandato por candidatura eleita (informada pelo TSE ou, em disputa de uma vaga que o TSE não fecha, derivada dos votos;
-- `base_eleicao` diz qual) (titular, vice e suplente eleito junto, de todos os cargos, inclusive vereador): o
-- mandato nasce da eleição, não do exercício. Quem assume depois como suplente é exercício (fatos.exercicios).
-- Início: a data de posse que o TSE informa na disputa vale quando cai no ano seguinte ao da eleição; fora disso o TSE
-- traz data impossível (posse antes da eleição, ano 8002) e ela não é usada. Só para prefeito e vice-prefeito a Constituição
-- fixa a posse (art. 29, III: 1º de janeiro do ano seguinte) e então ela é derivada. Nos demais cargos o início fica vazio
-- e o teste mede a lacuna. O fim é sempre derivado da duração do mandato na Constituição.
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

from {{ ref('fatos_candidaturas') }} as c

inner join {{ ref('int_tse_eleitos') }} as e on e.id_candidatura = c.id_candidatura

left join {{ ref('disputas') }} as d on d.id_disputa = c.id_disputa

left join {{ ref('eleicoes') }} as e on e.id_eleicao = d.id_eleicao

left join {{ ref('cargos') }} as k on k.id_cargo = d.id_cargo

cross join lateral (
    select
        case
            when year(d.dt_posse) = e.ano_eleicao + 1 then d.dt_posse
            when d.id_cargo in ('prefeito', 'vice_prefeito') then make_date(e.ano_eleicao + 1, 1, 1)
        end as dt_inicio,
        case
            when year(d.dt_posse) = e.ano_eleicao + 1 then 'informado'
            when d.id_cargo in ('prefeito', 'vice_prefeito') then 'derivado'
        end as base_dt_inicio
) as i

