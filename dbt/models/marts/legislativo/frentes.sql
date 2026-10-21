select
    '{{ var("source_camara") }}' as fonte,
    f.frente_id,
    f.titulo,
    f.criada_em,
    f.legislatura_id,
    f.situacao,
    i.id_pessoa as id_pessoa_coordenador

from {{ ref('stg_camara__frentes') }} as f

left join {{ ref('stg_identity__pessoa_identificadores') }} as i
    on i.fonte = '{{ var("source_camara") }}'
    and i.tipo_id = '{{ var("id_type_camara") }}'
    and i.id_na_fonte = cast(f.coordenador_deputado_id as varchar)
