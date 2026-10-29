{{ config(severity='warn') }}
-- A data da eleição de um turno é uma só para todas as unidades (DT_ELEICAO). Se o arquivo traz duas datas no mesmo
-- turno e eleição, dim_eleicoes guarda a primeira e o caso fica medido aqui.
select ano_eleicao, cd_eleicao, turno, count(distinct dt_eleicao) as datas

from {{ ref('stg_tse__candidaturas') }}

group by ano_eleicao, cd_eleicao, turno

having count(distinct dt_eleicao) > 1
