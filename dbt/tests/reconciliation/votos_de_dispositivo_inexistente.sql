-- Erro se há voto de um dispositivo vetado que não está em `dispositivos_vetados`.
select distinct v.dispositivo_id
from {{ ref('votos_em_vetos') }} as v
left join {{ ref('dispositivos_vetados') }} as d on d.dispositivo_id = v.dispositivo_id
where d.dispositivo_id is null
