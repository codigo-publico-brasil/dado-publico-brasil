{{ config(severity='warn') }}
-- Linhas de emenda em que algum valor veio preenchido na fonte e não virou número (formato inesperado).
select valor_empenhado, valor_liquidado, valor_pago
from {{ source('transparencia', 'emendas') }}
where (valor_empenhado is not null and try_cast(replace(valor_empenhado, ',', '.') as decimal(18, 2)) is null)
    or (valor_liquidado is not null and try_cast(replace(valor_liquidado, ',', '.') as decimal(18, 2)) is null)
    or (valor_pago is not null and try_cast(replace(valor_pago, ',', '.') as decimal(18, 2)) is null)
