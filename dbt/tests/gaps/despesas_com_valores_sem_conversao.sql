{{ config(severity='warn') }}
-- Linhas de despesa em que algum valor ou o mês veio preenchido na fonte e não virou número ou data (formato inesperado).
select valor_empenhado_rx, valor_liquidado_rx, valor_pago_rx, ano_e_m_s_do_lan_amento
from {{ source('transparencia', 'despesas') }}
where (valor_empenhado_rx is not null and try_cast(replace(valor_empenhado_rx, ',', '.') as decimal(18, 2)) is null)
    or (valor_liquidado_rx is not null and try_cast(replace(valor_liquidado_rx, ',', '.') as decimal(18, 2)) is null)
    or (valor_pago_rx is not null and try_cast(replace(valor_pago_rx, ',', '.') as decimal(18, 2)) is null)
    or (ano_e_m_s_do_lan_amento is not null and try_strptime(ano_e_m_s_do_lan_amento || '/01', '%Y/%m/%d') is null)
