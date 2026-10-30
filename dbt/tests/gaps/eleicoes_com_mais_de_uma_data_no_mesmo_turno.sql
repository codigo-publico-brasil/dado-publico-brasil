{{ config(severity='warn') }}
-- A data de um turno é uma só no país (DT_ELEICAO), com exceção rara: o 2º turno de Macapá em 2020 foi adiado para 20/12
-- (apagão no Amapá). dim_eleicoes guarda a primeira data e o caso fica medido aqui.
select ano_eleicao, turno, count(distinct dt_eleicao) as datas

from {{ ref('stg_tse__candidaturas') }}

group by ano_eleicao, turno

having count(distinct dt_eleicao) > 1
