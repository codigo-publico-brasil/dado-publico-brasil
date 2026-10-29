-- A chave de proposições, votações e votos é (fonte, id): o id sozinho só é único dentro da fonte.
select 'proposicoes' as mart, fonte, id_proposicao as id from {{ ref('fct_proposicoes') }}
group by fonte, id_proposicao having count(*) > 1

union all

select 'votacoes', fonte, id_votacao from {{ ref('fct_votacoes') }}
group by fonte, id_votacao having count(*) > 1

union all

select 'votos', fonte, id_votacao || '/' || id_pessoa from {{ ref('fct_votos') }}
group by fonte, id_votacao, id_pessoa having count(*) > 1

union all

select 'exercicios', fonte, id_exercicio from {{ ref('fct_exercicios') }}
group by fonte, id_exercicio having count(*) > 1

union all

select 'normas', fonte, cast(id_norma as varchar) from {{ ref('fct_normas') }}
group by fonte, id_norma having count(*) > 1

union all

select 'vetos', fonte, cast(id_veto as varchar) from {{ ref('fct_vetos') }}
group by fonte, id_veto having count(*) > 1

union all

select 'dispositivos_vetados', fonte, id_materia_veto || '/' || identificador from {{ ref('fct_vetos_dispositivos') }}
group by fonte, id_materia_veto, identificador having count(*) > 1

union all

select 'constituicao_dispositivos', parte, cast(ordem as varchar) from {{ ref('dim_constituicao_dispositivos') }}
group by parte, ordem having count(*) > 1
