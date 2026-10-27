-- Une a pessoa do projeto ao cadastro do Senado. Nascimento, naturalidade e foto vêm do detalhe do senador
-- (só dos já buscados); redes e site o Senado não informa nesses arquivos.
select
    i.id_pessoa,
    '{{ var("source_senado") }}' as fonte,
    s.nome,
    s.nome_civil,
    s.sexo,
    d.dt_nascimento as dt_nascimento,
    cast(null as date) as dt_falecimento,
    d.municipio_nascimento,
    d.uf_nascimento,
    d.foto_url,
    cast(null as varchar) as rede_social_url,
    cast(null as varchar) as site_url,
    cast(null as varchar) as escolaridade,
    cast(null as varchar) as situacao_atual,
    cast(null as varchar) as condicao_eleitoral,
    d.gabinete_email as email_institucional,
    d.gabinete_telefone as telefone_institucional,
    d.gabinete_endereco,
    d.pagina_url

from {{ ref('stg_identity__pessoa_identificadores') }} as i

inner join {{ ref('int_senadores_unidos') }} as s
    on i.fonte = '{{ var("source_senado") }}'
    and i.id_tipo = '{{ var("id_type_senado") }}'
    and i.id_na_fonte = cast(s.id_senador as varchar)

left join {{ ref('stg_senado__senadores_detalhe') }} as d on d.id_senador = s.id_senador
