select
    '{{ var("source_camara") }}' as fonte,
    f.id_frente,
    f.titulo,
    f.dt_criacao,
    f.id_legislatura,
    f.situacao,
    i.id_pessoa as id_pessoa_coordenador

from {{ ref('stg_camara__frentes') }} as f

left join {{ ref('stg_identity__pessoa_identificadores') }} as i
    on i.fonte = '{{ var("source_camara") }}'
    and i.id_tipo = '{{ var("id_type_camara") }}'
    and i.id_na_fonte = cast(f.id_coordenador_deputado as varchar)
