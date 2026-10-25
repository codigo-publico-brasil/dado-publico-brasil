-- Une a pessoa do projeto (chave própria) ao cadastro e aos dados vistos nos votos.
select
    i.id_pessoa,
    '{{ var("source_camara") }}' as fonte,
    d.id_deputado,
    coalesce(c.nome, n.nome) as nome,
    c.nome_civil,
    c.sexo,
    c.dt_nascimento,
    c.dt_falecimento,
    c.municipio_nascimento,
    c.uf_nascimento,
    coalesce(n.foto_url, f.foto_url) as foto_url,
    c.rede_social_url,
    c.site_url

from {{ ref('stg_identity__pessoa_identificadores') }} as i

inner join {{ ref('int_deputados_ids_unidos') }} as d
    on i.fonte = '{{ var("source_camara") }}'
    and i.id_tipo = '{{ var("id_type_camara") }}'
    and i.id_na_fonte = cast(d.id_deputado as varchar)

left join {{ ref('stg_camara__deputados') }} as c on c.id_deputado = d.id_deputado

left join {{ ref('int_deputados_votos_agregados') }} as n on n.id_deputado = d.id_deputado

left join {{ ref('int_deputados_frentes_fotos') }} as f on f.id_deputado = d.id_deputado
