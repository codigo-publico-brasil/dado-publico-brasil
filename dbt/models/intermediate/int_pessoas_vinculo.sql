-- Quem pode ser ligado entre fontes: pessoas das duas casas com nome civil (e nome parlamentar) e data de nascimento.
-- Câmara e Senado informam nome civil; o nascimento do Senado vem do detalhe do senador.
select
    '{{ var("source_camara") }}' as fonte,
    '{{ var("id_type_camara") }}' as id_tipo,
    cast(id_deputado as varchar) as id_na_fonte,
    name_key(nome_civil) as nome_chave,
    name_key(nome) as nome_urna_chave,
    dt_nascimento as dt_nascimento

from {{ ref('stg_camara__deputados') }}

union all

select
    '{{ var("source_senado") }}',
    '{{ var("id_type_senado") }}',
    cast(s.id_senador as varchar),
    name_key(s.nome_civil),
    name_key(p.nome),
    s.dt_nascimento

from {{ ref('stg_senado__senadores_detalhe') }} as s

left join {{ ref('stg_senado__senadores') }} as p on p.id_senador = s.id_senador
