{{ config(severity='warn') }}
-- Votações do Senado em que a maioria dos votantes que têm exercício oficial não estava em exercício na data da votação.
-- A fonte carimba datas impossíveis em votações antigas (a PEC 15/1998 sai com 2015 e senadores de 1999 a 2003); o voto
-- fica como a fonte publica, e a data dessas votações não é confiável (issue #100).
with votos as (

    select
        v.id_votacao,
        v.id_pessoa,
        v.dt_voto,
        exists (
            select 1 from {{ ref('fct_exercicios') }} as e
            where e.fonte = '{{ var("source_senado") }}' and e.id_pessoa = v.id_pessoa and v.dt_voto between e.dt_inicio and coalesce(e.dt_fim, date '9999-12-31')
        ) as em_exercicio,
        exists (select 1 from {{ ref('fct_exercicios') }} as e where e.fonte = '{{ var("source_senado") }}' and e.id_pessoa = v.id_pessoa) as tem_exercicio

    from {{ ref('int_votacoes_votos_ligados') }} as v

    where v.fonte = '{{ var("source_senado") }}'

)

select
    id_votacao,
    any_value(dt_voto) as dt_votacao,
    count(*) as qtd_votos,
    count(*) filter (where tem_exercicio and not em_exercicio) as qtd_votos_fora_do_exercicio

from votos

group by id_votacao

having count(*) filter (where tem_exercicio and not em_exercicio) * 2 > count(*)
