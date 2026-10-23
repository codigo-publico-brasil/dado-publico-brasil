{{ config(severity='warn') }}
-- Dispositivos que a fonte diz ter voto nominal e cujo voto ainda não foi buscado (o voto vem por amostra dos mais
-- recentes até a carga total ser pedida).
select d.dispositivo_id
from {{ ref('dispositivos_vetados') }} as d
where d.possui_votos
    and not exists (select 1 from {{ ref('votos_em_vetos') }} as v where v.dispositivo_id = d.dispositivo_id)
