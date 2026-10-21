select
    i.id_pessoa,
    string_agg(distinct p.titulo, ', ' order by p.titulo) as profissoes

from {{ ref('stg_camara__deputados_profissoes') }} as p

inner join {{ ref('stg_identity__pessoa_identificadores') }} as i
    on i.fonte = '{{ var("source_camara") }}'
    and i.tipo_id = '{{ var("id_type_camara") }}'
    and i.id_na_fonte = cast(p.deputado_id as varchar)

where p.titulo is not null

group by i.id_pessoa
