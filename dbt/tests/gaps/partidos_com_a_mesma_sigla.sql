{{ config(severity='warn') }}
-- Partidos que dividem a mesma sigla depois de tirar os asteriscos que a Câmara põe na sigla (a mesma sigla com um, dois ou três asteriscos).
-- Os asteriscos distinguem registros de partido com a mesma sigla; o significado exato não consta nas fontes que
-- consultamos, então a sigla original fica em `sigla_original` e o cruzamento por sigla precisa levar isso em conta.
select
    sigla,
    count(*) as registros

from {{ ref('dim_partidos_camara') }}

group by sigla

having count(*) > 1
