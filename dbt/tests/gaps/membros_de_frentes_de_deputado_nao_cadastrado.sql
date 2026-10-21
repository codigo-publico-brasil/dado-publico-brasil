{{ config(severity='warn') }}
-- Participações em frentes sem deputado identificado, ou de deputado que não está no cadastro nem nos
-- votos: ficam fora dos marts.
select s.deputado_id
from {{ ref('stg_camara__frentes_membros') }} as s
where not exists (select 1 from {{ ref('int_frentes_membros_ligados_a_pessoas') }} as m where m.deputado_id = s.deputado_id)
