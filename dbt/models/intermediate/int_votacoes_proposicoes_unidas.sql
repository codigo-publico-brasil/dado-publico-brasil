-- Une as proposições afetadas e as que são objeto de cada votação, com o papel de cada uma.
select votacao_id, proposicao_id, 'afetada' as papel from {{ ref('stg_camara__votacoes_proposicoes') }}

union all

select votacao_id, proposicao_id, 'objeto' as papel from {{ ref('stg_camara__votacoes_objetos') }}
