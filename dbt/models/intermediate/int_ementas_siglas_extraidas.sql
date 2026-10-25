-- Siglas que a fonte escreve em maiúsculas dentro de ementas de caixa mista (BNDES, CPI...).
-- Servem para não minusculizar a sigla quando uma ementa inteira está em maiúsculas.
with candidatas as (

    select unnest(regexp_extract_all(ementa, '\b[A-ZÀ-Ý]{2,10}\b')) as sigla

    from {{ ref('stg_camara__proposicoes') }}

    where ementa <> upper(ementa) and ementa <> lower(ementa)

)

select sigla

from candidatas

group by sigla

having count(*) >= 3
