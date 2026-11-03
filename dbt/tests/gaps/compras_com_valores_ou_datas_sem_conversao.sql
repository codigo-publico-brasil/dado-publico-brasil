{{ config(severity='warn') }}
-- Contratos em que algum valor ou data veio preenchido na fonte e não virou número ou data (formato inesperado).
select valor_inicial_compra, valor_final_compra, data_assinatura_contrato, data_in_cio_vig_ncia, data_fim_vig_ncia
from {{ source('transparencia', 'compras') }}
where (valor_inicial_compra is not null and try_cast(replace(valor_inicial_compra, ',', '.') as decimal(18, 2)) is null)
    or (valor_final_compra is not null and try_cast(replace(valor_final_compra, ',', '.') as decimal(18, 2)) is null)
    or (data_assinatura_contrato is not null and try_strptime(data_assinatura_contrato, '%d/%m/%Y') is null)
    or (data_in_cio_vig_ncia is not null and try_strptime(data_in_cio_vig_ncia, '%d/%m/%Y') is null)
    or (data_fim_vig_ncia is not null and try_strptime(data_fim_vig_ncia, '%d/%m/%Y') is null)
