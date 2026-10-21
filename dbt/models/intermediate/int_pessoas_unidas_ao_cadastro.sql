-- Une a pessoa do projeto (chave própria) ao cadastro e aos dados vistos nos votos.
select
    i.id_pessoa,
    d.deputado_id,
    coalesce(c.nome, n.nome) as nome,
    c.nome_civil,
    c.sexo,
    c.data_nascimento,
    c.data_falecimento,
    c.municipio_nascimento,
    c.uf_nascimento,
    coalesce(n.foto_url, f.foto_url) as foto_url,
    c.rede_social_url,
    c.site_url

from {{ ref('stg_identity__pessoa_identificadores') }} as i

inner join {{ ref('int_deputados_ids_unidos') }} as d
    on i.fonte = '{{ var("source_camara") }}'
    and i.tipo_id = '{{ var("id_type_camara") }}'
    and i.id_na_fonte = cast(d.deputado_id as varchar)

left join {{ ref('stg_camara__deputados') }} as c on c.deputado_id = d.deputado_id

left join {{ ref('int_deputados_nos_votos_agregados') }} as n on n.deputado_id = d.deputado_id

left join {{ ref('int_deputados_fotos_das_frentes') }} as f on f.deputado_id = d.deputado_id
