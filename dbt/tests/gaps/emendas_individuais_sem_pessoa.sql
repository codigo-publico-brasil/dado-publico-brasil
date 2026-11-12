{{ config(severity='warn') }}
-- Emendas individuais com autor informado que a regra do ADR 0056 não ligou a uma pessoa: nome sem correspondência,
-- ambíguo (homônimo com mandato) ou sem mandato federal no período. Ficam sem pessoa e são medidas aqui.
select cd_emenda, ano, cd_autor, autor_nome
from {{ ref('fct_emendas') }}
where tipo like 'Emenda Individual%' and autor_nome is not null and id_pessoa is null
