{{ config(severity='warn') }}
-- Despesas do CEAPS (Senado) que a fonte entrega sem número de documento (e, nas vistas, sem data de emissão).
-- É lacuna da própria fonte: o `id_documento` não é inventado; a linha segue com `hash_linha` (hash do conteúdo).
select hash_linha, tipo_despesa, ano, mes
from {{ ref('stg_senado__ceaps') }}
where id_documento is null
