-- Erro se um dispositivo vetado não tem o veto de que veio (os dispositivos são buscados a partir dos vetos).
select id_dispositivo from {{ ref('vetos_dispositivos') }} where id_veto is null
