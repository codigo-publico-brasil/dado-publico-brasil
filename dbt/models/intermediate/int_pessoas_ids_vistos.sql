-- Todo identificador de pessoa que as fontes informam. O código de identidade lê este modelo para dar a
-- cada um a chave própria de pessoa (regra conservadora: só o identificador oficial da própria fonte).
select
    '{{ var("source_camara") }}' as fonte,
    '{{ var("id_type_camara") }}' as id_tipo,
    cast(id_deputado as varchar) as id_na_fonte

from {{ ref('int_deputados_ids_unidos') }}

union

select
    '{{ var("source_senado") }}',
    '{{ var("id_type_senado") }}',
    cast(id_senador as varchar)

from {{ ref('int_senadores_unidos') }}
