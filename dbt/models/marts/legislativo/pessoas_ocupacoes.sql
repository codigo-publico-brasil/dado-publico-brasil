select
    i.id_pessoa,
    o.titulo,
    o.entidade,
    o.entidade_uf,
    o.ano_inicio,
    o.ano_inicio_original,
    o.ano_fim,
    o.ano_fim_original

from {{ ref('stg_camara__deputados_ocupacoes') }} as o

inner join {{ ref('stg_identity__pessoa_identificadores') }} as i
    on i.fonte = '{{ var("source_camara") }}'
    and i.id_tipo = '{{ var("id_type_camara") }}'
    and i.id_na_fonte = cast(o.id_deputado as varchar)
