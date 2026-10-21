-- Une a pessoa do projeto ao cadastro do Senado. O Senado não informa nascimento, foto nem redes
-- nos arquivos carregados: esses campos ficam vazios.
select
    i.id_pessoa,
    '{{ var("source_senado") }}' as fonte,
    s.nome,
    s.nome_civil,
    s.sexo,
    cast(null as date) as data_nascimento,
    cast(null as date) as data_falecimento,
    cast(null as varchar) as municipio_nascimento,
    cast(null as varchar) as uf_nascimento,
    cast(null as varchar) as foto_url,
    cast(null as varchar) as rede_social_url,
    cast(null as varchar) as site_url

from {{ ref('stg_identity__pessoa_identificadores') }} as i

inner join {{ ref('int_senadores_unidos') }} as s
    on i.fonte = '{{ var("source_senado") }}'
    and i.tipo_id = '{{ var("id_type_senado") }}'
    and i.id_na_fonte = cast(s.senador_id as varchar)
