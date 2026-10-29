{{ config(severity='warn') }}
-- Dispositivos que a fonte diz ter voto nominal e cujo voto ainda não foi buscado (o voto vem por amostra dos mais
-- recentes até a carga total ser pedida).
select d.id_dispositivo
from {{ ref('fct_vetos_dispositivos') }} as d
where d.fl_possui_votos
    and not exists (select 1 from {{ ref('fct_vetos_votos') }} as v where v.id_dispositivo = d.id_dispositivo)
