select
    i.id_pessoa,
    o.titulo,
    o.entidade,
    o.entidade_uf,
    o.ano_inicio,
    o.ano_fim

from {{ ref('stg_camara__deputados_ocupacoes') }} as o

inner join {{ ref('stg_identity__pessoa_identificadores') }} as i
    on i.fonte = '{{ var("source_camara") }}'
    and i.tipo_id = '{{ var("id_type_camara") }}'
    and i.id_na_fonte = cast(o.deputado_id as varchar)
