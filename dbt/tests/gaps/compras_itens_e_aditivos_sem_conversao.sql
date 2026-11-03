{{ config(severity='warn') }}
-- Itens e termos aditivos em que valor, quantidade ou data veio preenchido na fonte e não virou número ou data.
select 'compras_itens' as dataset, valor_item as valor_na_fonte
from {{ source('transparencia', 'compras_itens') }}
where (valor_item is not null and try_cast(replace(valor_item, ',', '.') as decimal(18, 2)) is null)
    or (quantidade_item is not null and try_cast(replace(quantidade_item, ',', '.') as decimal(18, 4)) is null)
union all
select 'compras_termos_aditivos', data_publica_o
from {{ source('transparencia', 'compras_termos_aditivos') }}
where data_publica_o is not null and try_strptime(data_publica_o, '%d/%m/%Y') is null
