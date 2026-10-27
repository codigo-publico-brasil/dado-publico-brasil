{{ config(severity='warn') }}
-- Disputas de uma vaga (presidente, governador, prefeito) de eleição ordinária sem nenhum mandato: o TSE não informa o
-- vencedor e a regra dos votos não fechou (votos não carregados, empate, candidatura inapta ou eleição em curso).
-- Cada linha é um mandato que falta na linha do tempo (issue 114).
select d.id_disputa, e.ano_eleicao, d.id_cargo
from {{ ref('disputas') }} as d
inner join {{ ref('eleicoes') }} as e on e.id_eleicao = d.id_eleicao
where e.fl_ordinaria
    and d.id_cargo in ('presidente', 'governador', 'prefeito')
    and not exists (select 1 from {{ ref('fatos_mandatos') }} as m where m.id_disputa = d.id_disputa)
