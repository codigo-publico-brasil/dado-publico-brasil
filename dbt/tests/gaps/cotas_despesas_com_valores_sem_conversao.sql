{{ config(severity='warn') }}
-- Despesas de cota em que um valor ou a data vieram preenchidos na fonte e não viraram número ou data (formato inesperado).
select 'camara' as fonte, vlr_documento as valor, dat_emissao as data
from {{ source('camara', 'cota_parlamentar') }}
where (vlr_documento is not null and try_cast(vlr_documento as decimal(18, 2)) is null)
    or (vlr_glosa is not null and try_cast(vlr_glosa as decimal(18, 2)) is null)
    or (vlr_liquido is not null and try_cast(vlr_liquido as decimal(18, 2)) is null)
    or (dat_emissao is not null and try_cast(dat_emissao as timestamp) is null)
union all
select 'senado', valor_reembolsado, data
from {{ source('senado', 'ceaps') }}
where (valor_reembolsado is not null and try_cast(replace(valor_reembolsado, ',', '.') as decimal(18, 2)) is null)
    or (data is not null and try_strptime(data, '%d/%m/%Y') is null)
