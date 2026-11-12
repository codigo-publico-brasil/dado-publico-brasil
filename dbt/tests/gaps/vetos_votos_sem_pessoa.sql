{{ config(severity='warn') }}
-- Votos nominais de veto que a regra do ADR 0057 não ligou a uma pessoa: nome sem correspondência, homônimo ou sem
-- exercício do cargo da casa, na UF, no dia da sessão. Ficam sem pessoa e são medidos aqui.
select id_dispositivo, casa, nome_parlamentar, uf
from {{ ref('fct_vetos_votos') }}
where id_pessoa is null
