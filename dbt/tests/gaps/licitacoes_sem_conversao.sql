{{ config(severity='warn') }}
-- Licitações, itens e empenhos em que valor, quantidade ou data veio preenchido na fonte e não virou número ou data.
select 'licitacoes' as dataset, valor_licita_o as valor_na_fonte
from {{ source('transparencia', 'licitacoes') }}
where (valor_licita_o is not null and try_cast(replace(valor_licita_o, ',', '.') as decimal(18, 4)) is null)
    or (data_resultado_compra is not null and try_strptime(data_resultado_compra, '%d/%m/%Y') is null)
    or (data_abertura is not null and try_strptime(data_abertura, '%d/%m/%Y') is null)
union all
select 'licitacoes_itens', valor_item
from {{ source('transparencia', 'licitacoes_itens') }}
where (valor_item is not null and try_cast(replace(valor_item, ',', '.') as decimal(18, 4)) is null)
    or (quantidade_item is not null and try_cast(replace(quantidade_item, ',', '.') as decimal(18, 4)) is null)
union all
select 'licitacoes_empenhos', valor_empenho_rx
from {{ source('transparencia', 'licitacoes_empenhos') }}
where (valor_empenho_rx is not null and try_cast(replace(valor_empenho_rx, ',', '.') as decimal(18, 4)) is null)
    or (data_emiss_o_empenho is not null and try_strptime(data_emiss_o_empenho, '%d/%m/%Y') is null)
union all
select 'licitacoes_participantes', flag_vencedor
from {{ source('transparencia', 'licitacoes_participantes') }}
where flag_vencedor is not null and upper(flag_vencedor) not in ('SIM', 'NÃO')
