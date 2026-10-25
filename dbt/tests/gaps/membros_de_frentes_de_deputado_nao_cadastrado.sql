{{ config(severity='warn') }}
-- Participações em frentes sem deputado identificado, ou de deputado que não está no cadastro nem nos
-- votos: ficam fora dos marts.
select s.id_deputado
from {{ ref('stg_camara__frentes_membros') }} as s
where not exists (select 1 from {{ ref('int_frentes_membros_ligados') }} as m where m.id_deputado = s.id_deputado)
