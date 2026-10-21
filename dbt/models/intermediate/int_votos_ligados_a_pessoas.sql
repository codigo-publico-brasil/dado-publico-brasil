select
    v.votacao_id,
    i.id_pessoa,
    v.voto,
    v.votou_em,
    v.partido_sigla,
    v.uf_sigla,
    v.legislatura_id,
    v.source_file_id

from {{ ref('stg_camara__votos') }} as v

inner join {{ ref('stg_identity__pessoa_identificadores') }} as i
    on i.fonte = '{{ var("source_camara") }}'
    and i.tipo_id = '{{ var("id_type_camara") }}'
    and i.id_na_fonte = cast(v.deputado_id as varchar)
