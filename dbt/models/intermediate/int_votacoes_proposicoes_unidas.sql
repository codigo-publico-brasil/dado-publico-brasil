-- Une as proposições afetadas e as que são objeto de cada votação, com o papel de cada uma.
select id_votacao, id_proposicao, 'afetada' as papel from {{ ref('stg_camara__votacoes_proposicoes') }}

union all

select id_votacao, id_proposicao, 'objeto' as papel from {{ ref('stg_camara__votacoes_objetos') }}
