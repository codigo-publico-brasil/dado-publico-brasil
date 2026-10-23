-- Une a pessoa do projeto ao cadastro do Senado. Nascimento, naturalidade e foto vêm do detalhe do senador
-- (só dos já buscados); redes e site o Senado não informa nesses arquivos.
select
    i.id_pessoa,
    '{{ var("source_senado") }}' as fonte,
    s.nome,
    s.nome_civil,
    s.sexo,
    d.nascimento as data_nascimento,
    cast(null as date) as data_falecimento,
    d.municipio_nascimento,
    d.uf_nascimento,
    d.foto_url,
    cast(null as varchar) as rede_social_url,
    cast(null as varchar) as site_url

from {{ ref('stg_identity__pessoa_identificadores') }} as i

inner join {{ ref('int_senadores_unidos') }} as s
    on i.fonte = '{{ var("source_senado") }}'
    and i.tipo_id = '{{ var("id_type_senado") }}'
    and i.id_na_fonte = cast(s.senador_id as varchar)

left join {{ ref('stg_senado__senadores_detalhe') }} as d on d.senador_id = s.senador_id
