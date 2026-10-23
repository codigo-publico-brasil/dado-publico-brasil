-- Erro se algum favorecido de emenda que não seja pessoa jurídica ou unidade gestora chegou aos marts (privacidade).
select favorecido_codigo
from {{ ref('emendas_favorecidos') }}
where tipo_favorecido not in ('Pessoa Jurídica', 'Unidade Gestora') or favorecido_codigo like '%*%'
