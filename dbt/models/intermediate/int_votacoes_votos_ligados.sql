-- Voto de cada pessoa em cada votação, de todas as fontes. O Senado só informa a data da sessão, então a
-- legislatura vem das datas oficiais das legislaturas (comuns às duas casas).
select
    '{{ var("source_camara") }}' as fonte,
    v.id_votacao,
    i.id_pessoa,
    v.voto,
    v.dt_voto,
    v.partido_sigla,
    v.uf_sigla,
    v.id_legislatura,
    v.id_captura

from {{ ref('stg_camara__votos') }} as v

inner join {{ ref('stg_identity__pessoa_identificadores') }} as i
    on i.fonte = '{{ var("source_camara") }}'
    and i.id_tipo = '{{ var("id_type_camara") }}'
    and i.id_na_fonte = cast(v.id_deputado as varchar)

union all

select
    '{{ var("source_senado") }}',
    cast(v.id_votacao as varchar),
    i.id_pessoa,
    v.voto,
    cast(d.dt_votacao as timestamp),
    v.partido_sigla,
    v.uf_sigla,
    l.id_legislatura,
    v.id_captura

from {{ ref('stg_senado__votos') }} as v

inner join {{ ref('stg_senado__votacoes') }} as d on d.id_votacao = v.id_votacao

inner join {{ ref('stg_identity__pessoa_identificadores') }} as i
    on i.fonte = '{{ var("source_senado") }}'
    and i.id_tipo = '{{ var("id_type_senado") }}'
    and i.id_na_fonte = cast(v.id_senador as varchar)

left join {{ ref('stg_camara__legislaturas') }} as l on d.dt_votacao between l.dt_inicio and l.dt_fim
