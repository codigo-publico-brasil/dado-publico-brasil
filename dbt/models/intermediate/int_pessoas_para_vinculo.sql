-- Quem pode ser ligado entre fontes: pessoas das duas casas com nome civil e data de nascimento.
-- Câmara e Senado informam nome civil; o nascimento do Senado vem do detalhe do senador.
select
    '{{ var("source_camara") }}' as fonte,
    '{{ var("id_type_camara") }}' as tipo_id,
    cast(deputado_id as varchar) as id_na_fonte,
    name_key(nome_civil) as nome_chave,
    data_nascimento as nascimento

from {{ ref('stg_camara__deputados') }}

union all

select
    '{{ var("source_senado") }}',
    '{{ var("id_type_senado") }}',
    cast(senador_id as varchar),
    name_key(nome_civil),
    nascimento

from {{ ref('stg_senado__senadores_detalhe') }}
