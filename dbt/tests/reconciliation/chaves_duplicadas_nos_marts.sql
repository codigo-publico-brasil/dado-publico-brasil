-- A chave de proposições, votações e votos é (fonte, id): o id sozinho só é único dentro da fonte.
select 'proposicoes' as mart, fonte, proposicao_id as id from {{ ref('proposicoes') }}
group by fonte, proposicao_id having count(*) > 1

union all

select 'votacoes', fonte, votacao_id from {{ ref('votacoes') }}
group by fonte, votacao_id having count(*) > 1

union all

select 'votos', fonte, votacao_id || '/' || id_pessoa from {{ ref('votos') }}
group by fonte, votacao_id, id_pessoa having count(*) > 1

union all

select 'exercicios', fonte, mandato_id || '/' || exercicio_id || '/' || id_pessoa from {{ ref('exercicios') }}
group by fonte, mandato_id, exercicio_id, id_pessoa having count(*) > 1

union all

select 'normas', fonte, cast(norma_id as varchar) from {{ ref('normas') }}
group by fonte, norma_id having count(*) > 1

union all

select 'vetos', fonte, cast(veto_id as varchar) from {{ ref('vetos') }}
group by fonte, veto_id having count(*) > 1

union all

select 'dispositivos_vetados', fonte, cast(dispositivo_id as varchar) from {{ ref('dispositivos_vetados') }}
group by fonte, dispositivo_id having count(*) > 1

union all

select 'constituicao_dispositivos', parte, cast(ordem as varchar) from {{ ref('constituicao_dispositivos') }}
group by parte, ordem having count(*) > 1
