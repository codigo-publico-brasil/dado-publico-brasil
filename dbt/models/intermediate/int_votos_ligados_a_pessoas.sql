-- Voto de cada pessoa em cada votação, de todas as fontes. O Senado só informa a data da sessão, então a
-- legislatura vem das datas oficiais das legislaturas (comuns às duas casas).
select
    '{{ var("source_camara") }}' as fonte,
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

union all

select
    '{{ var("source_senado") }}',
    cast(v.votacao_id as varchar),
    i.id_pessoa,
    v.voto,
    cast(d.data as timestamp),
    v.partido_sigla,
    v.uf_sigla,
    l.legislatura_id,
    v.source_file_id

from {{ ref('stg_senado__votos') }} as v

inner join {{ ref('stg_senado__votacoes') }} as d on d.votacao_id = v.votacao_id

inner join {{ ref('stg_identity__pessoa_identificadores') }} as i
    on i.fonte = '{{ var("source_senado") }}'
    and i.tipo_id = '{{ var("id_type_senado") }}'
    and i.id_na_fonte = cast(v.senador_id as varchar)

left join {{ ref('stg_camara__legislaturas') }} as l on d.data between l.inicio and l.fim
