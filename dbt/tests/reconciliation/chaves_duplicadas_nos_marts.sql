-- A chave de proposições, votações e votos é (fonte, id): o id sozinho só é único dentro da fonte.
select 'proposicoes' as mart, fonte, proposicao_id as id from {{ ref('proposicoes') }}
group by fonte, proposicao_id having count(*) > 1

union all

select 'votacoes', fonte, votacao_id from {{ ref('votacoes') }}
group by fonte, votacao_id having count(*) > 1

union all

select 'votos', fonte, votacao_id || '/' || id_pessoa from {{ ref('votos') }}
group by fonte, votacao_id, id_pessoa having count(*) > 1
