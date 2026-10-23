-- Erro se um dispositivo vetado não tem o veto de que veio (os dispositivos são buscados a partir dos vetos).
select dispositivo_id from {{ ref('dispositivos_vetados') }} where veto_id is null
