-- Erro se há voto de um dispositivo vetado que não está em `dispositivos_vetados`.
select distinct v.id_dispositivo
from {{ ref('fct_vetos_votos') }} as v
left join {{ ref('fct_vetos_dispositivos') }} as d on d.id_dispositivo = v.id_dispositivo
where d.id_dispositivo is null
